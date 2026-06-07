"""
GUSTO VPN Bot v2.0 — Production Ready
Читает конфиг из API, полный error handling, rate limiting, graceful shutdown
"""
import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from io import BytesIO

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    BufferedInputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.exceptions import TelegramRetryAfter, TelegramAPIError

import qrcode
from PIL import Image, ImageDraw, ImageFont

# ==================== LOGGING ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/var/log/gusto-bot.log") if os.path.exists("/var/log") else logging.StreamHandler()
    ]
)
logger = logging.getLogger("gusto.bot")

# ==================== CONFIGURATION (loaded from API) ====================
class BotConfig:
    """Динамическая конфигурация — загружается из backend API"""

    def __init__(self):
        self.bot_token: str = ""
        self.backend_url: str = "http://gusto-backend:8000"
        self.admin_ids: List[int] = []
        self.support_username: str = ""
        self.welcome_message: str = "Добро пожаловать в GUSTO VPN! 🚀"
        self.maintenance_mode: bool = False
        self._initialized: bool = False

    async def load(self, backend_url: str = None) -> bool:
        """Загрузить конфигурацию из backend API"""
        url = backend_url or self.backend_url
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get system settings (public endpoint)
                resp = await client.get(f"{url}/api/settings/health")
                if resp.status_code != 200:
                    logger.error(f"❌ Backend unavailable: {resp.status_code}")
                    return False

                health = resp.json()
                self.maintenance_mode = health.get("maintenance_mode", False)

                # Try to get full settings (may require auth, so catch 401)
                try:
                    settings_resp = await client.get(f"{url}/api/settings/")
                    if settings_resp.status_code == 200:
                        settings = settings_resp.json()
                        self.admin_ids = settings.get("admin_ids", [])
                        self.support_username = settings.get("support_username", "")
                        self.welcome_message = settings.get("welcome_message", self.welcome_message)
                        logger.info(f"✅ Loaded dynamic config: {len(self.admin_ids)} admins")
                    elif settings_resp.status_code == 401:
                        logger.warning("⚠️ Settings endpoint requires auth, using defaults for admin_ids")
                except Exception as e:
                    logger.warning(f"⚠️ Could not load full settings: {e}")

                self._initialized = True
                return True

        except Exception as e:
            logger.error(f"❌ Failed to load config: {e}")
            return False

    def is_admin(self, telegram_id: int) -> bool:
        return telegram_id in self.admin_ids

# Global config instance
config = BotConfig()

# ==================== HTTP CLIENT (with retries) ====================
class BackendClient:
    """HTTP клиент с retry, backoff и circuit breaker"""

    def __init__(self, base_url: str, max_retries: int = 3):
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self._circuit_open: bool = False
        self._circuit_failures: int = 0
        self._circuit_threshold: int = 5
        self._circuit_reset_time: Optional[datetime] = None

        limits = httpx.Limits(max_connections=50, max_keepalive_connections=20)
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0),
            limits=limits,
            http2=True
        )

    async def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Выполнить запрос с retry и circuit breaker"""

        # Circuit breaker check
        if self._circuit_open:
            if self._circuit_reset_time and datetime.utcnow() > self._circuit_reset_time:
                self._circuit_open = False
                self._circuit_failures = 0
                logger.info("🔓 Circuit breaker reset")
            else:
                logger.warning("⛔ Circuit breaker OPEN — skipping request")
                return {"error": True, "detail": "Service temporarily unavailable"}

        url = f"{self.base_url}{endpoint}"

        for attempt in range(self.max_retries):
            try:
                resp = await self.client.request(method, url, **kwargs)

                if resp.status_code == 200:
                    self._circuit_failures = 0
                    return resp.json()

                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 5))
                    logger.warning(f"⏳ Rate limited, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue

                if resp.status_code in (401, 403):
                    logger.error(f"❌ Auth error {resp.status_code} for {endpoint}")
                    return {"error": True, "detail": f"HTTP {resp.status_code}", "status_code": resp.status_code}

                if resp.status_code in (500, 502, 503, 504):
                    self._circuit_failures += 1
                    if self._circuit_failures >= self._circuit_threshold:
                        self._circuit_open = True
                        self._circuit_reset_time = datetime.utcnow() + timedelta(minutes=2)
                        logger.error("🔒 Circuit breaker OPENED")

                    wait = 2 ** attempt
                    logger.warning(f"🔄 Server error {resp.status_code}, retry in {wait}s (attempt {attempt+1})")
                    await asyncio.sleep(wait)
                    continue

                logger.error(f"❌ HTTP {resp.status_code}: {resp.text[:200]}")
                return {"error": True, "detail": f"HTTP {resp.status_code}", "status_code": resp.status_code}

            except httpx.ConnectError as e:
                logger.error(f"❌ Connection error: {e}")
                self._circuit_failures += 1
                wait = 2 ** attempt
                await asyncio.sleep(wait)

            except httpx.TimeoutException:
                logger.warning(f"⏱️ Timeout (attempt {attempt+1})")
                wait = 2 ** attempt
                await asyncio.sleep(wait)

            except Exception as e:
                logger.error(f"❌ Unexpected error: {e}")
                return {"error": True, "detail": str(e)}

        return {"error": True, "detail": "Max retries exceeded"}

    async def get_user(self, telegram_id: int) -> Optional[Dict]:
        result = await self._request("GET", f"/api/users/telegram/{telegram_id}")
        if result and not result.get("error"):
            return result
        return None

    async def create_user(self, data: Dict) -> Optional[Dict]:
        return await self._request("POST", "/api/users/", json=data)

    async def get_plans(self) -> List[Dict]:
        result = await self._request("GET", "/api/plans/?is_active=true")
        return result if result and not result.get("error") else []

    async def create_subscription(self, data: Dict) -> Optional[Dict]:
        return await self._request("POST", "/api/subscriptions/pending", json=data)

    async def get_user_subscriptions(self, user_id: int) -> List[Dict]:
        result = await self._request("GET", f"/api/subscriptions/?user_id={user_id}")
        return result if result and not result.get("error") else []

    async def get_subscription(self, sub_id: int) -> Optional[Dict]:
        return await self._request("GET", f"/api/subscriptions/{sub_id}")

    async def create_payment(self, data: Dict) -> Optional[Dict]:
        return await self._request("POST", "/api/payments/", json=data)

    async def get_payment_status(self, payment_id: int) -> Optional[Dict]:
        return await self._request("GET", f"/api/payments/{payment_id}")

    async def get_referral_stats(self, user_id: int) -> Optional[Dict]:
        return await self._request("GET", f"/api/referrals/stats/{user_id}")

    async def close(self):
        await self.client.aclose()

# ==================== RATE LIMITER ====================
class RateLimiter:
    """Rate limiter для рассылок и API вызовов"""

    def __init__(self, max_rate: float = 1.0, burst: int = 5):
        self.max_rate = max_rate
        self.burst = burst
        self.tokens = burst
        self.last_update = datetime.utcnow()
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = datetime.utcnow()
            elapsed = (now - self.last_update).total_seconds()
            self.tokens = min(self.burst, self.tokens + elapsed * self.max_rate)
            self.last_update = now

            if self.tokens < 1:
                wait = (1 - self.tokens) / self.max_rate
                await asyncio.sleep(wait)
                self.tokens = 0
            else:
                self.tokens -= 1

# Global instances
backend: Optional[BackendClient] = None
rate_limiter = RateLimiter(max_rate=1.0, burst=5)

# ==================== QR GENERATOR ====================
def generate_qr_code(config_link: str, caption: str = "") -> BytesIO:
    """Сгенерировать QR-код с подписью"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(config_link)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img = img.convert("RGB")

    if caption:
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), caption, font=font)
        text_width = bbox[2] - bbox[0]
        img_width = img.size[0]

        new_img = Image.new("RGB", (img_width, img.size[1] + 40), "white")
        new_img.paste(img, (0, 0))
        draw = ImageDraw.Draw(new_img)
        draw.text(((img_width - text_width) // 2, img.size[1] + 10), caption, fill="black", font=font)
        img = new_img

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

# ==================== FSM STATES ====================
class BuyFlow(StatesGroup):
    select_plan = State()
    select_payment = State()
    waiting_payment = State()

class RenewFlow(StatesGroup):
    select_subscription = State()
    select_plan = State()
    waiting_payment = State()

class SupportFlow(StatesGroup):
    write_message = State()

class AdminFlow(StatesGroup):
    select_action = State()
    broadcast_message = State()
    add_server = State()

# ==================== KEYBOARDS ====================
def main_menu_kb(is_admin: bool = False):
    buttons = [
        [InlineKeyboardButton(text="🛒 Купить VPN", callback_data="buy")],
        [InlineKeyboardButton(text="👤 Мой кабинет", callback_data="account")],
        [InlineKeyboardButton(text="👥 Партнерка", callback_data="referral")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="support")],
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="🔧 Админ-панель", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def back_kb(callback_data: str = "main"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback_data)]
    ])

# ==================== MAINTENANCE MIDDLEWARE ====================
class MaintenanceMiddleware:
    """Проверка maintenance mode перед каждым обновлением"""

    async def __call__(self, handler, event, data):
        if isinstance(event, Message) and config.maintenance_mode:
            if not config.is_admin(event.from_user.id):
                await event.answer(
                    "🔧 **Технические работы**\n\n"
                    "Сервис временно недоступен.\n"
                    "Попробуйте позже."
                )
                return
        return await handler(event, data)

# ==================== BOT INIT ====================
async def init_bot() -> tuple[Bot, Dispatcher]:
    """Инициализация бота с загрузкой конфигурации"""

    # Load from environment first (required for token)
    bot_token = os.getenv("BOT_TOKEN", "")
    backend_url = os.getenv("BACKEND_URL", "http://gusto-backend:8000")
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/1")

    if not bot_token:
        logger.error("❌ BOT_TOKEN not set! Set environment variable BOT_TOKEN")
        sys.exit(1)

    # Load dynamic config from backend
    config.backend_url = backend_url
    loaded = await config.load(backend_url)
    if not loaded:
        logger.warning("⚠️ Could not load dynamic config, using defaults")

    # Initialize global backend client
    global backend
    backend = BackendClient(backend_url)

    # Initialize bot
    storage = RedisStorage.from_url(redis_url)
    bot = Bot(token=bot_token, parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=storage)

    # Register middleware
    dp.message.middleware(MaintenanceMiddleware())
    dp.callback_query.middleware(MaintenanceMiddleware())

    logger.info("✅ Bot initialized successfully")
    return bot, dp

# ==================== HANDLERS ====================

def register_handlers(dp: Dispatcher):
    """Регистрация всех handlers"""

    @dp.message(CommandStart())
    async def cmd_start(message: Message, state: FSMContext):
        await state.clear()

        if not backend:
            await message.answer("❌ Сервис временно недоступен. Попробуйте позже.")
            return

        telegram_id = message.from_user.id
        username = message.from_user.username
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name

        # Check referral
        ref_code = None
        if message.text and len(message.text.split()) > 1:
            payload = message.text.split()[1]
            if payload.startswith("ref_"):
                ref_code = payload.replace("ref_", "")

        # Get or create user
        try:
            user = await backend.get_user(telegram_id)
            if not user:
                user_data = {
                    "telegram_id": telegram_id,
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "referred_by": int(ref_code) if ref_code and ref_code.isdigit() else None
                }
                user = await backend.create_user(user_data)
                if user and not user.get("error"):
                    logger.info(f"✅ New user registered: {telegram_id}")
        except Exception as e:
            logger.error(f"❌ Error getting/creating user: {e}")
            await message.answer("❌ Ошибка регистрации. Попробуйте позже.")
            return

        is_admin = user.get("is_admin", False) if user and not user.get("error") else False

        welcome_text = (
            f"🚀 **Добро пожаловать в GUSTO VPN!**\n\n"
            f"Привет, {first_name}! 👋\n\n"
            f" **Что такое GUSTO?**\n"
            f"• ⚡ Максимальная скорость (XTLS-Reality)\n"
            f"• 🌍 10+ серверов в Европе и Азии\n"
            f"• 🔒 Военное шифрование\n"
            f"• 📱 До 5 устройств\n"
            f"• 💰 Оплата картой, криптой, СБП\n\n"
            f" _Быстрый. Безопасный. Без границ._\n\n"
            f"Выберите действие 👇"
        )

        await message.answer(welcome_text, reply_markup=main_menu_kb(is_admin))

    @dp.callback_query(F.data == "buy")
    async def cb_buy(callback: CallbackQuery, state: FSMContext):
        await state.set_state(BuyFlow.select_plan)

        if not backend:
            await callback.answer("❌ Сервис недоступен", show_alert=True)
            return

        try:
            plans = await backend.get_plans()
        except Exception as e:
            logger.error(f"❌ Error loading plans: {e}")
            await callback.answer("❌ Ошибка загрузки тарифов", show_alert=True)
            return

        if not plans:
            await callback.message.edit_text(
                "😔 **Тарифы временно недоступны**\n\n"
                "Попробуйте позже или обратитесь в поддержку.",
                reply_markup=back_kb("main")
            )
            return

        kb_buttons = []
        for plan in plans:
            if not plan.get("is_active", True):
                continue

            name = plan.get("display_name") or plan.get("name", "Без названия")
            price = plan.get("price", 0)
            traffic = plan.get("traffic_gb", 0)
            days = plan.get("duration_days", 30)

            label = f"⚡ {name} — {price}₽ ({traffic}GB / {days}д)"
            if plan.get("is_popular"):
                label = f"🔥 {label}"

            kb_buttons.append([
                InlineKeyboardButton(text=label, callback_data=f"plan:{plan['id']}")
            ])

        kb_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="main")])

        await callback.message.edit_text(
            "📋 **GUSTO Тарифы**\n\n"
            "Все тарифы включают:\n"
            "• ⚡ VLESS + Reality (обход DPI)\n"
            "• 🔄 Smart Router (автовыбор сервера)\n"
            "• 📱 До 5 устройств\n"
            "• 🛡️ GUSTO Shield (антифрод)\n"
            "• 💬 Поддержка 24/7\n\n"
            " _⭐ Популярный выбор — GUSTO Про_",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons)
        )

    @dp.callback_query(F.data.startswith("plan:"), BuyFlow.select_plan)
    async def cb_select_plan(callback: CallbackQuery, state: FSMContext):
        plan_id = int(callback.data.split(":")[1])

        try:
            plans = await backend.get_plans()
        except Exception as e:
            logger.error(f"❌ Error loading plans: {e}")
            await callback.answer("❌ Ошибка", show_alert=True)
            return

        plan = next((p for p in plans if p["id"] == plan_id), None)
        if not plan:
            await callback.answer("❌ Тариф не найден", show_alert=True)
            return

        await state.update_data(plan_id=plan_id, plan=plan)
        await state.set_state(BuyFlow.select_payment)

        name = plan.get("display_name") or plan.get("name")
        price = plan.get("price", 0)
        traffic = plan.get("traffic_gb", 0)
        days = plan.get("duration_days", 30)

        payment_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 CryptoBot", callback_data="pay:crypto")],
            [InlineKeyboardButton(text="💳 ЮKassa", callback_data="pay:yookassa")],
            [InlineKeyboardButton(text="💵 FreeKassa", callback_data="pay:freekassa")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="buy")]
        ])

        await callback.message.edit_text(
            f"✅ **{name}**\n\n"
            f"📊 Трафик: **{traffic} GB**\n"
            f"📅 Срок: **{days} дней**\n"
            f"💰 Сумма: **{price}₽**\n\n"
            f"Выберите способ оплаты:",
            reply_markup=payment_kb
        )

    @dp.callback_query(F.data.startswith("pay:"), BuyFlow.select_payment)
    async def cb_select_payment(callback: CallbackQuery, state: FSMContext):
        method = callback.data.split(":")[1]
        methods = {"crypto": "CryptoBot", "yookassa": "ЮKassa", "freekassa": "FreeKassa"}

        data = await state.get_data()
        plan = data.get("plan")

        if not plan:
            await callback.answer("❌ Ошибка: тариф не выбран", show_alert=True)
            return

        # Get user
        try:
            user = await backend.get_user(callback.from_user.id)
        except Exception as e:
            logger.error(f"❌ Error getting user: {e}")
            await callback.answer("❌ Ошибка", show_alert=True)
            return

        if not user or user.get("error"):
            await callback.answer("❌ Ошибка: пользователь не найден", show_alert=True)
            return

        # Create pending subscription
        try:
            sub_data = {
                "user_id": user["id"],
                "plan_id": plan["id"],
                "country_code": "RU",
                "payment_method": method
            }
            sub = await backend.create_subscription(sub_data)
        except Exception as e:
            logger.error(f"❌ Error creating subscription: {e}")
            await callback.answer("❌ Ошибка создания подписки", show_alert=True)
            return

        if not sub or sub.get("error"):
            await callback.answer("❌ Ошибка создания подписки", show_alert=True)
            return

        # Create payment
        try:
            payment_data = {
                "user_id": user["id"],
                "subscription_id": sub["subscription_id"],
                "plan_id": plan["id"],
                "provider": method,
                "amount": plan["price"],
                "currency": "RUB"
            }
            payment = await backend.create_payment(payment_data)
        except Exception as e:
            logger.error(f"❌ Error creating payment: {e}")
            await callback.answer("❌ Ошибка создания платежа", show_alert=True)
            return

        if not payment or payment.get("error"):
            await callback.answer("❌ Ошибка создания платежа", show_alert=True)
            return

        await state.update_data(
            subscription_id=sub["subscription_id"],
            payment_id=payment["id"],
            plan=plan
        )
        await state.set_state(BuyFlow.waiting_payment)

        pay_url = payment.get("pay_url", "")
        amount = payment.get("amount", plan["price"])

        await callback.message.edit_text(
            f"🏦 **Оплата через {methods.get(method)}**\n\n"
            f"Сумма: **{amount}₽**\n"
            f"Тариф: **{plan.get('display_name') or plan['name']}**\n\n"
            f"Нажмите кнопку ниже для оплаты.\n"
            f"После оплаты нажмите **🔄 Проверить оплату**.\n\n"
            f" _⏳ У вас есть 30 минут для оплаты_",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 Перейти к оплате", url=pay_url)],
                [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_pay:{payment['id']}")],
                [InlineKeyboardButton(text="◀️ Отменить", callback_data="cancel_payment")]
            ])
        )

    @dp.callback_query(F.data.startswith("check_pay:"))
    async def cb_check_payment(callback: CallbackQuery, state: FSMContext):
        payment_id = int(callback.data.split(":")[1])

        await callback.answer("⏳ Проверяем оплату...", show_alert=False)

        try:
            payment = await backend.get_payment_status(payment_id)
        except Exception as e:
            logger.error(f"❌ Error checking payment: {e}")
            await callback.answer("❌ Ошибка проверки", show_alert=True)
            return

        if not payment or payment.get("error"):
            await callback.answer("❌ Ошибка проверки", show_alert=True)
            return

        status = payment.get("status", "pending")

        if status == "success":
            await state.clear()

            # Get subscription details
            data = await state.get_data()
            sub_id = data.get("subscription_id")
            plan = data.get("plan", {})

            if sub_id:
                try:
                    sub = await backend.get_subscription(sub_id)
                except Exception as e:
                    logger.error(f"❌ Error getting subscription: {e}")
                    sub = None

                if sub and not sub.get("error"):
                    config_link = sub.get("config_link", "")
                    plan_name = sub.get("plan", {}).get("name", "GUSTO VPN")
                    server_name = sub.get("server", {}).get("name", "GUSTO")

                    # Generate QR
                    try:
                        qr_buf = generate_qr_code(config_link, f"GUSTO VPN - {server_name}")
                        qr_file = BufferedInputFile(qr_buf.getvalue(), filename="config_qr.png")

                        await callback.message.delete()
                        await callback.message.answer_photo(
                            photo=qr_file,
                            caption=(
                                f"🎉 **Оплата успешна!**\n\n"
                                f"✅ Подписка **{plan_name}** активирована\n\n"
                                f"🔑 **Ваша конфигурация:**\n"
                                f" `{config_link}`\n\n"
                                f"📱 **Как подключить:**\n"
                                f"1. **Android:** V2RayNG или NekoBox\n"
                                f"2. **iOS:** Streisand или Shadowrocket\n"
                                f"3. **Windows:** NekoRay или v2rayN\n"
                                f"4. **macOS:** V2RayXS или V2RayU\n\n"
                                f"Отсканируйте QR-код или скопируйте ссылку! 🚀"
                            ),
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="📋 Копировать конфиг", callback_data=f"copy_config:{sub_id}")],
                                [InlineKeyboardButton(text="📊 Мой кабинет", callback_data="account")]
                            ])
                        )
                    except Exception as e:
                        logger.error(f"❌ QR generation failed: {e}")
                        # Fallback without QR
                        await callback.message.edit_text(
                            f"🎉 **Оплата успешна!**\n\n"
                            f"✅ Подписка **{plan_name}** активирована\n\n"
                            f"🔑 **Ваша конфигурация:**\n"
                            f" `{config_link}`\n\n"
                            f"📱 **Как подключить:**\n"
                            f"1. Android: V2RayNG или NekoBox\n"
                            f"2. iOS: Streisand или Shadowrocket\n"
                            f"3. Windows: NekoRay или v2rayN\n"
                            f"4. macOS: V2RayXS или V2RayU\n\n"
                            f"Скопируйте ссылку и вставьте в приложение! 🚀",
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="📋 Копировать конфиг", callback_data=f"copy_config:{sub_id}")],
                                [InlineKeyboardButton(text="📊 Мой кабинет", callback_data="account")]
                            ])
                        )
                    return

            await callback.message.edit_text(
                "🎉 **Оплата успешна!**\n\n"
                "Ваша подписка активируется в течение минуты.\n"
                "Проверьте раздел 'Мой кабинет'.",
                reply_markup=main_menu_kb()
            )

        elif status == "failed":
            await callback.answer("❌ Платеж не удался. Попробуйте снова.", show_alert=True)

        else:
            await callback.answer("⏳ Платеж еще обрабатывается... Попробуйте через минуту.", show_alert=True)

    @dp.callback_query(F.data == "cancel_payment")
    async def cb_cancel_payment(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        await callback.message.edit_text(
            "❌ **Оплата отменена**\n\n"
            "Вы можете попробовать снова в любое время.",
            reply_markup=main_menu_kb()
        )

    # ==================== ACCOUNT ====================

    @dp.callback_query(F.data == "account")
    async def cb_account(callback: CallbackQuery):
        try:
            user = await backend.get_user(callback.from_user.id)
        except Exception as e:
            logger.error(f"❌ Error getting user: {e}")
            await callback.answer("❌ Ошибка загрузки профиля", show_alert=True)
            return

        if not user or user.get("error"):
            await callback.answer("❌ Ошибка загрузки профиля", show_alert=True)
            return

        try:
            subs = await backend.get_user_subscriptions(user["id"])
        except Exception as e:
            logger.error(f"❌ Error getting subscriptions: {e}")
            subs = []

        active_subs = [s for s in subs if s.get("status") == "active"]

        subs_text = ""
        if active_subs:
            for sub in active_subs:
                expires = sub.get("expires_at", "")
                days_left = "?"
                if expires:
                    try:
                        expires_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                        days_left = (expires_dt - datetime.now(expires_dt.tzinfo)).days
                    except:
                        pass

                traffic_used = sub.get("used_gb", 0)
                traffic_total = sub.get("total_gb", 0)
                server_name = sub.get("server", {}).get("name", "N/A")
                flag = sub.get("server", {}).get("flag_emoji", "")

                subs_text += (
                    f"📡 {server_name} {flag}\n"
                    f" 📅 {days_left}д | 📊 {traffic_used:.1f}/{traffic_total}GB\n"
                )
        else:
            subs_text = "❌ Нет активных подписок\n"

        await callback.message.edit_text(
            f"👤 **Мой GUSTO**\n\n"
            f"├ ID: `{user['id']}`\n"
            f"├ Подписки: {len(active_subs)} активных\n"
            f"├ 💰 Баланс: {float(user.get('referral_balance', 0)):.2f}₽\n"
            f"├ 👥 Рефералов: {user.get('referral_count', 0)}\n"
            f"└ 🏆 Уровень: {user.get('referral_level', 0)}\n\n"
            f" **Активные подписки:**\n{subs_text}\n"
            f" `https://t.me/gustovpn_bot?start=ref_{user['id']}`",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📊 Мои подписки", callback_data="subs")],
                [InlineKeyboardButton(text="🔑 Получить конфиг", callback_data="config")],
                [InlineKeyboardButton(text="🔄 Продлить", callback_data="renew")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="main")]
            ])
        )

    @dp.callback_query(F.data == "subs")
    async def cb_subs(callback: CallbackQuery):
        try:
            user = await backend.get_user(callback.from_user.id)
            if not user or user.get("error"):
                return
            subs = await backend.get_user_subscriptions(user["id"])
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return

        if not subs:
            await callback.message.edit_text(
                "📊 **Мои подписки**\n\n"
                "У вас пока нет подписок.\n"
                "Купите VPN в главном меню!",
                reply_markup=back_kb("account")
            )
            return

        kb_buttons = []
        for sub in subs:
            status_emoji = "🟢" if sub.get("status") == "active" else "🔴"
            name = sub.get("server", {}).get("name", "N/A")
            flag = sub.get("server", {}).get("flag_emoji", "")
            kb_buttons.append([
                InlineKeyboardButton(text=f"{status_emoji} {name} {flag}", callback_data=f"sub_detail:{sub['id']}")
            ])

        kb_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="account")])

        await callback.message.edit_text(
            f"📊 **Мои подписки**\n\n"
            f"Всего: {len(subs)}\n"
            f"Активных: {len([s for s in subs if s.get('status') == 'active'])}\n\n"
            f"Выберите подписку для подробностей:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons)
        )

    @dp.callback_query(F.data.startswith("sub_detail:"))
    async def cb_sub_detail(callback: CallbackQuery):
        sub_id = int(callback.data.split(":")[1])

        try:
            sub = await backend.get_subscription(sub_id)
        except Exception as e:
            logger.error(f"❌ Error getting subscription: {e}")
            await callback.answer("❌ Ошибка", show_alert=True)
            return

        if not sub or sub.get("error"):
            await callback.answer("❌ Подписка не найдена", show_alert=True)
            return

        config_link = sub.get("config_link", "")
        expires = sub.get("expires_at", "")
        days_left = "?"
        if expires:
            try:
                expires_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                days_left = (expires_dt - datetime.now(expires_dt.tzinfo)).days
            except:
                pass

        traffic_used = sub.get("used_gb", 0)
        traffic_total = sub.get("total_gb", 0)
        server = sub.get("server", {})

        await callback.message.edit_text(
            f"📡 **Подписка #{sub_id}**\n\n"
            f"🌍 Сервер: {server.get('name', 'N/A')} {server.get('flag_emoji', '')}\n"
            f"🔒 Протокол: {sub.get('protocol', 'vless').upper()} + {sub.get('security', 'reality').upper()}\n"
            f"📅 Действует до: {expires[:10] if expires else 'N/A'}\n"
            f"⏳ Осталось: {days_left} дней\n"
            f"📊 Трафик: {traffic_used:.1f} / {traffic_total} GB\n\n"
            f"🔑 **Конфигурация:**\n"
            f" `{config_link}`",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Копировать", callback_data=f"copy_config:{sub_id}")],
                [InlineKeyboardButton(text="📷 QR-код", callback_data=f"qr_config:{sub_id}")],
                [InlineKeyboardButton(text="🔄 Продлить", callback_data=f"renew_sub:{sub_id}")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="subs")]
            ])
        )

    @dp.callback_query(F.data.startswith("copy_config:"))
    async def cb_copy_config(callback: CallbackQuery):
        sub_id = int(callback.data.split(":")[1])

        try:
            sub = await backend.get_subscription(sub_id)
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            await callback.answer("❌ Ошибка", show_alert=True)
            return

        if not sub or sub.get("error"):
            await callback.answer("❌ Ошибка", show_alert=True)
            return

        config_link = sub.get("config_link", "")

        await callback.message.answer(
            f"🔑 **Ваша конфигурация:**\n\n"
            f" `{config_link}`\n\n"
            f"Нажмите на ссылку выше, чтобы скопировать.\n\n"
            f"📱 **Как подключить:**\n"
            f"1. **Android:** V2RayNG или NekoBox\n"
            f"2. **iOS:** Streisand или Shadowrocket\n"
            f"3. **Windows:** NekoRay или v2rayN\n"
            f"4. **macOS:** V2RayXS или V2RayU\n\n"
            f"Вставьте ссылку в приложение и подключайтесь! 🚀"
        )
        await callback.answer("✅ Конфигурация отправлена")

    @dp.callback_query(F.data.startswith("qr_config:"))
    async def cb_qr_config(callback: CallbackQuery):
        sub_id = int(callback.data.split(":")[1])

        try:
            sub = await backend.get_subscription(sub_id)
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            await callback.answer("❌ Ошибка", show_alert=True)
            return

        if not sub or sub.get("error"):
            await callback.answer("❌ Ошибка", show_alert=True)
            return

        config_link = sub.get("config_link", "")
        server_name = sub.get("server", {}).get("name", "GUSTO")

        try:
            qr_buf = generate_qr_code(config_link, f"GUSTO VPN - {server_name}")
            qr_file = BufferedInputFile(qr_buf.getvalue(), filename="config_qr.png")

            await callback.message.answer_photo(
                photo=qr_file,
                caption=f"📷 **QR-код для {server_name}**\n\n"
                      f"Отсканируйте в приложении V2RayNG/Streisand"
            )
            await callback.answer("✅ QR-код отправлен")
        except Exception as e:
            logger.error(f"❌ QR generation failed: {e}")
            await callback.answer("❌ Ошибка генерации QR", show_alert=True)

    # ==================== RENEW ====================

    @dp.callback_query(F.data == "renew")
    async def cb_renew(callback: CallbackQuery, state: FSMContext):
        try:
            user = await backend.get_user(callback.from_user.id)
            if not user or user.get("error"):
                return
            subs = await backend.get_user_subscriptions(user["id"])
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return

        active_subs = [s for s in subs if s.get("status") == "active"]

        if not active_subs:
            await callback.answer("❌ Нет активных подписок для продления", show_alert=True)
            return

        await state.set_state(RenewFlow.select_subscription)

        kb_buttons = []
        for sub in active_subs:
            name = sub.get("server", {}).get("name", "N/A")
            flag = sub.get("server", {}).get("flag_emoji", "")
            kb_buttons.append([
                InlineKeyboardButton(text=f"🔄 {name} {flag}", callback_data=f"renew_select:{sub['id']}")
            ])

        kb_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="account")])

        await callback.message.edit_text(
            "🔄 **Продление подписки**\n\n"
            "Выберите подписку для продления:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons)
        )

    @dp.callback_query(F.data.startswith("renew_select:"), RenewFlow.select_subscription)
    async def cb_renew_select(callback: CallbackQuery, state: FSMContext):
        sub_id = int(callback.data.split(":")[1])
        await state.update_data(renew_sub_id=sub_id)
        await state.set_state(RenewFlow.select_plan)

        try:
            plans = await backend.get_plans()
        except Exception as e:
            logger.error(f"❌ Error loading plans: {e}")
            await callback.answer("❌ Ошибка", show_alert=True)
            return

        kb_buttons = []
        for plan in plans:
            if not plan.get("is_active", True):
                continue
            name = plan.get("display_name") or plan.get("name")
            price = plan.get("price", 0)
            traffic = plan.get("traffic_gb", 0)
            days = plan.get("duration_days", 30)

            kb_buttons.append([
                InlineKeyboardButton(
                    text=f"⚡ {name} — {price}₽ ({traffic}GB / {days}д)",
                    callback_data=f"renew_plan:{plan['id']}"
                )
            ])

        kb_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="renew")])

        await callback.message.edit_text(
            "🔄 **Выберите тариф для продления**\n\n"
            "Вы можете продлить на тот же или другой тариф:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons)
        )

    # ==================== REFERRAL ====================

    @dp.callback_query(F.data == "referral")
    async def cb_referral(callback: CallbackQuery):
        try:
            user = await backend.get_user(callback.from_user.id)
            if not user or user.get("error"):
                await callback.answer("❌ Ошибка", show_alert=True)
                return

            stats = await backend.get_referral_stats(user["id"])
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            stats = {"total_referrals": 0, "total_earned": 0, "referral_balance": 0, "level": 0}

        if not stats or stats.get("error"):
            stats = {"total_referrals": 0, "total_earned": 0, "referral_balance": 0, "level": 0}

        ref_link = f"https://t.me/gustovpn_bot?start=ref_{user['id']}"

        await callback.message.edit_text(
            f"🤝 **GUSTO Партнерка**\n\n"
            f"Приглашайте друзей и зарабатывайте!\n\n"
            f" **Уровни комиссии:**\n"
            f"• 🥇 1 уровень: **30%**\n"
            f"• 🥈 2 уровень: **15%**\n"
            f"• 🥉 3 уровень: **5%**\n\n"
            f" **Ваша статистика:**\n"
            f"├ Рефералов: {stats.get('total_referrals', 0)}\n"
            f"├ Заработано: {float(stats.get('total_earned', 0)):.2f}₽\n"
            f"├ Баланс: {float(stats.get('referral_balance', 0)):.2f}₽\n"
            f"└ Уровень: {stats.get('level', 0)}\n\n"
            f" **Ваша ссылка:**\n"
            f" `{ref_link}`\n\n"
            f"Минимум для вывода: 500₽",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Копировать ссылку", callback_data="copy_ref")],
                [InlineKeyboardButton(text="💰 Вывести", callback_data="withdraw")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="main")]
            ])
        )

    @dp.callback_query(F.data == "copy_ref")
    async def cb_copy_ref(callback: CallbackQuery):
        try:
            user = await backend.get_user(callback.from_user.id)
            if user and not user.get("error"):
                ref_link = f"https://t.me/gustovpn_bot?start=ref_{user['id']}"
                await callback.message.answer(f"🔗 **Ваша реферальная ссылка:** `{ref_link}`")
                await callback.answer("✅ Ссылка отправлена")
        except Exception as e:
            logger.error(f"❌ Error: {e}")

    # ==================== SUPPORT ====================

    @dp.callback_query(F.data == "support")
    async def cb_support(callback: CallbackQuery, state: FSMContext):
        await state.set_state(SupportFlow.write_message)

        support_link = f"https://t.me/{config.support_username}" if config.support_username else ""

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📨 Написать поддержке", url=support_link)] if support_link else [],
            [InlineKeyboardButton(text="✏️ Написать сюда", callback_data="write_support")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="main")]
        ])

        await callback.message.edit_text(
            "❓ **GUSTO Support**\n\n"
            "Если нужна помощь:\n"
            "• Пишите: @gusto_support\n"
            "• Или напишите сюда сообщение\n\n"
            " _GUSTO — Быстрый. Безопасный. Без границ._",
            reply_markup=kb
        )

    @dp.callback_query(F.data == "write_support")
    async def cb_write_support(callback: CallbackQuery, state: FSMContext):
        await state.set_state(SupportFlow.write_message)
        await callback.message.edit_text(
            "✏️ **Напишите ваше сообщение:**\n\n"
            "Опишите проблему или вопрос.\n"
            "Мы ответим в ближайшее время.",
            reply_markup=back_kb("support")
        )

    @dp.message(SupportFlow.write_message)
    async def support_message(message: Message, state: FSMContext):
        try:
            user = await backend.get_user(message.from_user.id)
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            user = None

        support_text = (
            f"📩 **Новое обращение**\n\n"
            f"От: {message.from_user.full_name} (@{message.from_user.username or 'N/A'})\n"
            f"ID: `{message.from_user.id}`\n"
            f"User ID: {user['id'] if user and not user.get('error') else 'N/A'}\n\n"
            f"Сообщение:\n{message.text}"
        )

        # Send to admins with rate limiting
        for admin_id in config.admin_ids:
            try:
                await rate_limiter.acquire()
                await bot.send_message(admin_id, support_text, parse_mode=ParseMode.HTML)
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
                try:
                    await bot.send_message(admin_id, support_text, parse_mode=ParseMode.HTML)
                except Exception as e2:
                    logger.error(f"❌ Failed to send to admin {admin_id}: {e2}")
            except Exception as e:
                logger.error(f"❌ Failed to send to admin {admin_id}: {e}")

        await message.answer(
            "✅ **Сообщение отправлено!**\n\n"
            "Мы ответим вам в ближайшее время.\n"
            "Обычно ответ занимает до 2 часов.",
            reply_markup=main_menu_kb()
        )
        await state.clear()

    # ==================== ADMIN PANEL ====================

    @dp.callback_query(F.data == "admin")
    async def cb_admin(callback: CallbackQuery, state: FSMContext):
        if not config.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен", show_alert=True)
            return

        await state.set_state(AdminFlow.select_action)

        await callback.message.edit_text(
            "🔧 **Админ-панель GUSTO**\n\n"
            "Выберите действие:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
                [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
                [InlineKeyboardButton(text="📡 Серверы", callback_data="admin_servers")],
                [InlineKeyboardButton(text="💰 Платежи", callback_data="admin_payments")],
                [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
                [InlineKeyboardButton(text="➕ Добавить сервер", callback_data="admin_add_server")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="main")]
            ])
        )

    @dp.callback_query(F.data == "admin_broadcast")
    async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext):
        if not config.is_admin(callback.from_user.id):
            return

        await state.set_state(AdminFlow.broadcast_message)
        await callback.message.edit_text(
            "📢 **Массовая рассылка**\n\n"
            "Введите сообщение для отправки всем пользователям:\n"
            " _Поддерживается HTML-разметка_",
            reply_markup=back_kb("admin")
        )

    @dp.message(AdminFlow.broadcast_message)
    async def admin_broadcast_message(message: Message, state: FSMContext):
        if not config.is_admin(message.from_user.id):
            await state.clear()
            return

        broadcast_text = message.text

        try:
            # Get all users from backend
            users = await backend._request("GET", "/api/users/")
            if not users or users.get("error"):
                await message.answer("❌ Ошибка получения списка пользователей")
                return
        except Exception as e:
            logger.error(f"❌ Error getting users: {e}")
            await message.answer("❌ Ошибка")
            return

        sent = 0
        failed = 0

        await message.answer("⏳ Рассылка началась...")

        for u in users:
            try:
                await rate_limiter.acquire()  # 1 msg/sec
                await bot.send_message(u["telegram_id"], broadcast_text, parse_mode=ParseMode.HTML)
                sent += 1
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
                try:
                    await bot.send_message(u["telegram_id"], broadcast_text, parse_mode=ParseMode.HTML)
                    sent += 1
                except:
                    failed += 1
            except Exception:
                failed += 1

            # Progress update every 30 messages
            if (sent + failed) % 30 == 0:
                await message.answer(f"⏳ Отправлено: {sent}, Ошибок: {failed}")

        await message.answer(
            f"✅ **Рассылка завершена!**\n\n"
            f"📤 Отправлено: {sent}\n"
            f"❌ Ошибок: {failed}",
            reply_markup=main_menu_kb(is_admin=True)
        )
        await state.clear()

    # ==================== BACK TO MAIN ====================

    @dp.callback_query(F.data == "main")
    async def cb_main(callback: CallbackQuery, state: FSMContext):
        await state.clear()

        try:
            user = await backend.get_user(callback.from_user.id)
            is_admin = user.get("is_admin", False) if user and not user.get("error") else False
        except:
            is_admin = False

        await callback.message.edit_text(
            "🚀 **GUSTO VPN**\n\n"
            "Выберите действие 👇",
            reply_markup=main_menu_kb(is_admin)
        )

    # ==================== ERROR HANDLERS ====================

    @dp.errors()
    async def error_handler(event):
        logger.error(f"❌ Unhandled error: {event.exception}", exc_info=True)

        # Try to notify user
        if event.update.message:
            try:
                await event.update.message.answer(
                    "❌ **Произошла ошибка**\n\n"
                    "Мы уже работаем над исправлением.\n"
                    "Попробуйте позже."
                )
            except:
                pass
        elif event.update.callback_query:
            try:
                await event.update.callback_query.answer(
                    "❌ Произошла ошибка. Попробуйте позже.",
                    show_alert=True
                )
            except:
                pass

        return True

# ==================== MAIN ====================
async def main():
    """Главная функция с graceful shutdown"""

    # Initialize bot
    bot, dp = await init_bot()

    # Register handlers
    register_handlers(dp)

    # Setup graceful shutdown
    shutdown_event = asyncio.Event()

    async def shutdown(signal_name: str):
        logger.info(f"🛑 Received {signal_name}, shutting down...")
        shutdown_event.set()

        # Close backend client
        if backend:
            await backend.close()

        # Close bot session
        await bot.session.close()

        logger.info("✅ Shutdown complete")

    # Register signal handlers
    import signal
    for sig in (signal.SIGTERM, signal.SIGINT):
        asyncio.get_event_loop().add_signal_handler(
            sig, lambda s=sig: asyncio.create_task(shutdown(signal.Signals(s).name))
        )

    logger.info("🚀 GUSTO Bot starting polling...")

    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Bot crashed: {e}", exc_info=True)
    finally:
        await shutdown("FINALLY")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 KeyboardInterrupt received")
    except Exception as e:
        logger.critical(f"💥 Fatal error: {e}", exc_info=True)
        sys.exit(1)
