"""
GUSTO VPN Bot — Полноценная интеграция с Backend API + QR + Notifications
Быстрый. Безопасный. Без границ.
"""
import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from io import BytesIO

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    BufferedInputFile, InputMediaPhoto
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.redis import RedisStorage

# QR generation
import qrcode
from PIL import Image, ImageDraw, ImageFont

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gusto.bot")

# ==================== CONFIG ====================
BOT_TOKEN = "YOUR_BOT_TOKEN"
BACKEND_URL = "http://gusto-backend:8000"
REDIS_URL = "redis://localhost:6379/1"
SUPPORT_USERNAME = "gusto_support"
ADMIN_IDS = [123456789]  # Telegram IDs админов

# ==================== HTTP CLIENT ====================
class BackendClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        url = f"{self.base_url}{endpoint}"
        try:
            resp = await self.client.request(method, url, **kwargs)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Error {e.response.status_code}: {e.response.text}")
            return {"error": True, "detail": e.response.text}
        except Exception as e:
            logger.error(f"Request error: {e}")
            return {"error": True, "detail": str(e)}

    async def get_user(self, telegram_id: int) -> Optional[Dict]:
        result = await self._request("GET", "/api/users/")
        if result and not result.get("error"):
            for user in result:
                if user.get("telegram_id") == telegram_id:
                    return user
        return None

    async def create_user(self, data: Dict) -> Optional[Dict]:
        return await self._request("POST", "/api/users/", json=data)

    async def get_plans(self) -> List[Dict]:
        result = await self._request("GET", "/api/plans/")
        return result if result and not result.get("error") else []

    async def create_subscription(self, data: Dict) -> Optional[Dict]:
        return await self._request("POST", "/api/subscriptions/", json=data)

    async def get_user_subscriptions(self, user_id: int) -> List[Dict]:
        result = await self._request("GET", f"/api/subscriptions/?user_id={user_id}")
        return result if result and not result.get("error") else []

    async def get_subscription(self, sub_id: int) -> Optional[Dict]:
        return await self._request("GET", f"/api/subscriptions/{sub_id}")

    async def renew_subscription(self, sub_id: int, data: Dict) -> Optional[Dict]:
        return await self._request("POST", f"/api/subscriptions/{sub_id}/renew", json=data)

    async def create_payment(self, data: Dict) -> Optional[Dict]:
        return await self._request("POST", "/api/payments/", json=data)

    async def get_payment_status(self, payment_id: int) -> Optional[Dict]:
        return await self._request("GET", f"/api/payments/{payment_id}")

    async def get_referral_stats(self, user_id: int) -> Optional[Dict]:
        return await self._request("GET", f"/api/referrals/stats/{user_id}")

backend = BackendClient(BACKEND_URL)

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
    img = img.convert('RGB')

    # Add caption
    if caption:
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except:
            font = ImageFont.load_default()

        # Calculate text position
        bbox = draw.textbbox((0, 0), caption, font=font)
        text_width = bbox[2] - bbox[0]
        img_width = img.size[0]

        # Create new image with space for text
        new_img = Image.new('RGB', (img_width, img.size[1] + 40), 'white')
        new_img.paste(img, (0, 0))
        draw = ImageDraw.Draw(new_img)
        draw.text(((img_width - text_width) // 2, img.size[1] + 10), caption, fill="black", font=font)
        img = new_img

    buf = BytesIO()
    img.save(buf, format='PNG')
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

# ==================== BOT INIT ====================
storage = RedisStorage.from_url(REDIS_URL)
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=storage)

# ==================== HANDLERS ====================

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

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

    is_admin = user.get("is_admin", False) if user and not user.get("error") else False

    welcome_text = (
        f"🚀 <b>Добро пожаловать в GUSTO VPN!</b>

"
        f"Привет, {first_name}! 👋

"
        f"<b>Что такое GUSTO?</b>
"
        f"• ⚡ Максимальная скорость (XTLS-Reality)
"
        f"• 🌍 10+ серверов в Европе и Азии
"
        f"• 🔒 Военное шифрование
"
        f"• 📱 До 5 устройств
"
        f"• 💰 Оплата картой, криптой, СБП

"
        f"<i>Быстрый. Безопасный. Без границ.</i>

"
        f"Выберите действие 👇"
    )

    await message.answer(welcome_text, reply_markup=main_menu_kb(is_admin))

# ==================== BUY FLOW ====================

@dp.callback_query(F.data == "buy")
async def cb_buy(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BuyFlow.select_plan)

    plans = await backend.get_plans()
    if not plans:
        await callback.message.edit_text(
            "😔 <b>Тарифы временно недоступны</b>

"
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
        "📋 <b>GUSTO Тарифы</b>

"
        "Все тарифы включают:
"
        "• ⚡ VLESS + Reality (обход DPI)
"
        "• 🔄 Smart Router (автовыбор сервера)
"
        "• 📱 До 5 устройств
"
        "• 🛡️ GUSTO Shield (антифрод)
"
        "• 💬 Поддержка 24/7

"
        "<i>⭐ Популярный выбор — GUSTO Про</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    )

@dp.callback_query(F.data.startswith("plan:"), BuyFlow.select_plan)
async def cb_select_plan(callback: CallbackQuery, state: FSMContext):
    plan_id = int(callback.data.split(":")[1])

    plans = await backend.get_plans()
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
        f"✅ <b>{name}</b>

"
        f"📊 Трафик: <b>{traffic} GB</b>
"
        f"📅 Срок: <b>{days} дней</b>
"
        f"💰 Сумма: <b>{price}₽</b>

"
        f"Выберите способ оплаты:",
        reply_markup=payment_kb
    )

@dp.callback_query(F.data.startswith("pay:"), BuyFlow.select_payment)
async def cb_select_payment(callback: CallbackQuery, state: FSMContext):
    method = callback.data.split(":")[1]
    methods = {
        "crypto": "CryptoBot",
        "yookassa": "ЮKassa",
        "freekassa": "FreeKassa"
    }

    data = await state.get_data()
    plan = data.get("plan")

    if not plan:
        await callback.answer("❌ Ошибка: тариф не выбран", show_alert=True)
        return

    # Get user
    user = await backend.get_user(callback.from_user.id)
    if not user or user.get("error"):
        await callback.answer("❌ Ошибка: пользователь не найден", show_alert=True)
        return

    # Create subscription (pending)
    sub_data = {
        "user_id": user["id"],
        "plan_id": plan["id"],
        "country_code": "RU",
        "payment_method": method
    }

    sub = await backend.create_subscription(sub_data)
    if not sub or sub.get("error"):
        await callback.answer("❌ Ошибка создания подписки", show_alert=True)
        return

    await state.update_data(subscription_id=sub["subscription_id"], payment_id=sub["payment_id"])
    await state.set_state(BuyFlow.waiting_payment)

    pay_url = sub.get("pay_url", "")
    amount = sub.get("amount", plan["price"])

    await callback.message.edit_text(
        f"🏦 <b>Оплата через {methods.get(method)}</b>

"
        f"Сумма: <b>{amount}₽</b>
"
        f"Тариф: <b>{plan.get('display_name') or plan['name']}</b>

"
        f"Нажмите кнопку ниже для оплаты.
"
        f"После оплаты нажмите <b>🔄 Проверить оплату</b>.

"
        f"<i>⏳ У вас есть 30 минут для оплаты</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Перейти к оплате", url=pay_url)],
            [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_pay:{sub['payment_id']}")],
            [InlineKeyboardButton(text="◀️ Отменить", callback_data="cancel_payment")]
        ])
    )

@dp.callback_query(F.data.startswith("check_pay:"))
async def cb_check_payment(callback: CallbackQuery, state: FSMContext):
    payment_id = int(callback.data.split(":")[1])

    # Show loading
    await callback.answer("⏳ Проверяем оплату...", show_alert=False)

    payment = await backend.get_payment_status(payment_id)
    if not payment or payment.get("error"):
        await callback.answer("❌ Ошибка проверки", show_alert=True)
        return

    status = payment.get("status", "pending")

    if status == "success":
        await state.clear()

        # Get subscription details
        data = await state.get_data()
        sub_id = data.get("subscription_id")

        if sub_id:
            sub = await backend.get_subscription(sub_id)
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
                            f"🎉 <b>Оплата успешна!</b>

"
                            f"✅ Подписка <b>{plan_name}</b> активирована

"
                            f"🔑 <b>Ваша конфигурация:</b>
"
                            f"<code>{config_link}</code>

"
                            f"📱 <b>Как подключить:</b>
"
                            f"1. <b>Android:</b> V2RayNG или NekoBox
"
                            f"2. <b>iOS:</b> Streisand или Shadowrocket
"
                            f"3. <b>Windows:</b> NekoRay или v2rayN
"
                            f"4. <b>macOS:</b> V2RayXS или V2RayU

"
                            f"Отсканируйте QR-код или скопируйте ссылку! 🚀"
                        ),
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="📋 Копировать конфиг", callback_data=f"copy_config:{sub_id}")],
                            [InlineKeyboardButton(text="📊 Мой кабинет", callback_data="account")]
                        ])
                    )
                except Exception as e:
                    logger.error(f"QR generation failed: {e}")
                    # Fallback without QR
                    await callback.message.edit_text(
                        f"🎉 <b>Оплата успешна!</b>

"
                        f"✅ Подписка <b>{plan_name}</b> активирована

"
                        f"🔑 <b>Ваша конфигурация:</b>
"
                        f"<code>{config_link}</code>

"
                        f"📱 <b>Как подключить:</b>
"
                        f"1. Android: V2RayNG или NekoBox
"
                        f"2. iOS: Streisand или Shadowrocket
"
                        f"3. Windows: NekoRay или v2rayN
"
                        f"4. macOS: V2RayXS или V2RayU

"
                        f"Скопируйте ссылку и вставьте в приложение! 🚀",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="📋 Копировать конфиг", callback_data=f"copy_config:{sub_id}")],
                            [InlineKeyboardButton(text="📊 Мой кабинет", callback_data="account")]
                        ])
                    )
                return

        await callback.message.edit_text(
            "🎉 <b>Оплата успешна!</b>

"
            "Ваша подписка активируется в течение минуты.
"
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
        "❌ <b>Оплата отменена</b>

"
        "Вы можете попробовать снова в любое время.",
        reply_markup=main_menu_kb()
    )

# ==================== ACCOUNT ====================

@dp.callback_query(F.data == "account")
async def cb_account(callback: CallbackQuery):
    user = await backend.get_user(callback.from_user.id)
    if not user or user.get("error"):
        await callback.answer("❌ Ошибка загрузки профиля", show_alert=True)
        return

    subs = await backend.get_user_subscriptions(user["id"])
    active_subs = [s for s in subs if s.get("status") == "active"]

    subs_text = ""
    if active_subs:
        for sub in active_subs:
            expires = sub.get("expires_at", "")
            if expires:
                try:
                    expires_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                    days_left = (expires_dt - datetime.now(expires_dt.tzinfo)).days
                except:
                    days_left = "?"
            else:
                days_left = "?"

            traffic_used = sub.get("used_gb", 0)
            traffic_total = sub.get("total_gb", 0)

            subs_text += (
                f"📡 {sub.get('server', {}).get('name', 'N/A')} {sub.get('server', {}).get('flag_emoji', '')}
"
                f"   📅 {days_left}д | 📊 {traffic_used:.1f}/{traffic_total}GB
"
            )
    else:
        subs_text = "❌ Нет активных подписок
"

    await callback.message.edit_text(
        f"👤 <b>Мой GUSTO</b>

"
        f"├ ID: <code>{user['id']}</code>
"
        f"├ Подписки: {len(active_subs)} активных
"
        f"├ 💰 Баланс: {float(user.get('referral_balance', 0)):.2f}₽
"
        f"├ 👥 Рефералов: {user.get('referral_count', 0)}
"
        f"└ 🏆 Уровень: {user.get('referral_level', 0)}

"
        f"<b>Активные подписки:</b>
{subs_text}
"
        f"<code>https://t.me/gustovpn_bot?start=ref_{user['id']}</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Мои подписки", callback_data="subs")],
            [InlineKeyboardButton(text="🔑 Получить конфиг", callback_data="config")],
            [InlineKeyboardButton(text="🔄 Продлить", callback_data="renew")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="main")]
        ])
    )

@dp.callback_query(F.data == "subs")
async def cb_subs(callback: CallbackQuery):
    user = await backend.get_user(callback.from_user.id)
    if not user or user.get("error"):
        return

    subs = await backend.get_user_subscriptions(user["id"])

    if not subs:
        await callback.message.edit_text(
            "📊 <b>Мои подписки</b>

"
            "У вас пока нет подписок.

"
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
            InlineKeyboardButton(
                text=f"{status_emoji} {name} {flag}",
                callback_data=f"sub_detail:{sub['id']}"
            )
        ])

    kb_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="account")])

    await callback.message.edit_text(
        "📊 <b>Мои подписки</b>

"
        f"Всего: {len(subs)}
"
        f"Активных: {len([s for s in subs if s.get('status') == 'active'])}

"
        "Выберите подписку для подробностей:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    )

@dp.callback_query(F.data.startswith("sub_detail:"))
async def cb_sub_detail(callback: CallbackQuery):
    sub_id = int(callback.data.split(":")[1])

    sub = await backend.get_subscription(sub_id)
    if not sub or sub.get("error"):
        await callback.answer("❌ Подписка не найдена", show_alert=True)
        return

    config_link = sub.get("config_link", "")
    expires = sub.get("expires_at", "")

    try:
        expires_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
        days_left = (expires_dt - datetime.now(expires_dt.tzinfo)).days
    except:
        days_left = "?"

    traffic_used = sub.get("used_gb", 0)
    traffic_total = sub.get("total_gb", 0)
    server = sub.get("server", {})

    await callback.message.edit_text(
        f"📡 <b>Подписка #{sub_id}</b>

"
        f"🌍 Сервер: {server.get('name', 'N/A')} {server.get('flag_emoji', '')}
"
        f"🔒 Протокол: {sub.get('protocol', 'vless').upper()} + {sub.get('security', 'reality').upper()}
"
        f"📅 Действует до: {expires[:10] if expires else 'N/A'}
"
        f"⏳ Осталось: {days_left} дней
"
        f"📊 Трафик: {traffic_used:.1f} / {traffic_total} GB

"
        f"🔑 <b>Конфигурация:</b>
"
        f"<code>{config_link}</code>",
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

    sub = await backend.get_subscription(sub_id)
    if not sub or sub.get("error"):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    config_link = sub.get("config_link", "")

    await callback.message.answer(
        f"🔑 <b>Ваша конфигурация:</b>

"
        f"<code>{config_link}</code>

"
        f"Нажмите на ссылку выше, чтобы скопировать.

"
        f"📱 <b>Как подключить:</b>
"
        f"1. <b>Android:</b> V2RayNG или NekoBox
"
        f"2. <b>iOS:</b> Streisand или Shadowrocket
"
        f"3. <b>Windows:</b> NekoRay или v2rayN
"
        f"4. <b>macOS:</b> V2RayXS или V2RayU

"
        f"Вставьте ссылку в приложение и подключайтесь! 🚀"
    )
    await callback.answer("✅ Конфигурация отправлена")

@dp.callback_query(F.data.startswith("qr_config:"))
async def cb_qr_config(callback: CallbackQuery):
    sub_id = int(callback.data.split(":")[1])

    sub = await backend.get_subscription(sub_id)
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
            caption=f"📷 <b>QR-код для {server_name}</b>

"
                    f"Отсканируйте в приложении V2RayNG/Streisand"
        )
        await callback.answer("✅ QR-код отправлен")
    except Exception as e:
        logger.error(f"QR generation failed: {e}")
        await callback.answer("❌ Ошибка генерации QR", show_alert=True)

# ==================== RENEW ====================

@dp.callback_query(F.data == "renew")
async def cb_renew(callback: CallbackQuery, state: FSMContext):
    user = await backend.get_user(callback.from_user.id)
    if not user or user.get("error"):
        return

    subs = await backend.get_user_subscriptions(user["id"])
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
            InlineKeyboardButton(
                text=f"🔄 {name} {flag}",
                callback_data=f"renew_select:{sub['id']}"
            )
        ])

    kb_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="account")])

    await callback.message.edit_text(
        "🔄 <b>Продление подписки</b>

"
        "Выберите подписку для продления:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    )

@dp.callback_query(F.data.startswith("renew_select:"), RenewFlow.select_subscription)
async def cb_renew_select(callback: CallbackQuery, state: FSMContext):
    sub_id = int(callback.data.split(":")[1])

    await state.update_data(renew_sub_id=sub_id)
    await state.set_state(RenewFlow.select_plan)

    # Show plans for renewal
    plans = await backend.get_plans()

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
        "🔄 <b>Выберите тариф для продления</b>

"
        "Вы можете продлить на тот же или другой тариф:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    )

@dp.callback_query(F.data.startswith("renew_plan:"), RenewFlow.select_plan)
async def cb_renew_plan(callback: CallbackQuery, state: FSMContext):
    plan_id = int(callback.data.split(":")[1])

    data = await state.get_data()
    sub_id = data.get("renew_sub_id")

    # Get plan details
    plans = await backend.get_plans()
    plan = next((p for p in plans if p["id"] == plan_id), None)

    if not plan:
        await callback.answer("❌ Тариф не найден", show_alert=True)
        return

    # Create payment for renewal
    user = await backend.get_user(callback.from_user.id)
    if not user or user.get("error"):
        return

    payment_data = {
        "user_id": user["id"],
        "subscription_id": sub_id,
        "plan_id": plan_id,
        "amount": float(plan["price"]),
        "currency": "RUB",
        "method": "yookassa"  # Default, can be changed
    }

    payment = await backend.create_payment(payment_data)
    if not payment or payment.get("error"):
        await callback.answer("❌ Ошибка создания платежа", show_alert=True)
        return

    await state.update_data(renew_payment_id=payment["id"])
    await state.set_state(RenewFlow.waiting_payment)

    await callback.message.edit_text(
        f"🔄 <b>Продление подписки</b>

"
        f"Тариф: <b>{plan.get('display_name') or plan['name']}</b>
"
        f"Сумма: <b>{plan['price']}₽</b>

"
        f"Выберите способ оплаты:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 CryptoBot", callback_data=f"renew_pay:crypto:{payment['id']}")],
            [InlineKeyboardButton(text="💳 ЮKassa", callback_data=f"renew_pay:yookassa:{payment['id']}")],
            [InlineKeyboardButton(text="💵 FreeKassa", callback_data=f"renew_pay:freekassa:{payment['id']}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="renew")]
        ])
    )

# ==================== REFERRAL ====================

@dp.callback_query(F.data == "referral")
async def cb_referral(callback: CallbackQuery):
    user = await backend.get_user(callback.from_user.id)
    if not user or user.get("error"):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    stats = await backend.get_referral_stats(user["id"])
    if not stats or stats.get("error"):
        stats = {
            "total_referrals": 0,
            "total_earned": 0,
            "referral_balance": 0,
            "level": 0
        }

    ref_link = f"https://t.me/gustovpn_bot?start=ref_{user['id']}"

    await callback.message.edit_text(
        f"🤝 <b>GUSTO Партнерка</b>

"
        f"Приглашайте друзей и зарабатывайте!

"
        f"<b>Уровни комиссии:</b>
"
        f"• 🥇 1 уровень: <b>30%</b>
"
        f"• 🥈 2 уровень: <b>15%</b>
"
        f"• 🥉 3 уровень: <b>5%</b>

"
        f"<b>Ваша статистика:</b>
"
        f"├ Рефералов: {stats.get('total_referrals', 0)}
"
        f"├ Заработано: {float(stats.get('total_earned', 0)):.2f}₽
"
        f"├ Баланс: {float(stats.get('referral_balance', 0)):.2f}₽
"
        f"└ Уровень: {stats.get('level', 0)}

"
        f"<b>Ваша ссылка:</b>
"
        f"<code>{ref_link}</code>

"
        f"Минимум для вывода: 500₽",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Копировать ссылку", callback_data="copy_ref")],
            [InlineKeyboardButton(text="💰 Вывести", callback_data="withdraw")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="main")]
        ])
    )

@dp.callback_query(F.data == "copy_ref")
async def cb_copy_ref(callback: CallbackQuery):
    user = await backend.get_user(callback.from_user.id)
    if user and not user.get("error"):
        ref_link = f"https://t.me/gustovpn_bot?start=ref_{user['id']}"
        await callback.message.answer(f"🔗 <b>Ваша реферальная ссылка:</b>

<code>{ref_link}</code>")
    await callback.answer("✅ Ссылка отправлена")

# ==================== SUPPORT ====================

@dp.callback_query(F.data == "support")
async def cb_support(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SupportFlow.write_message)

    await callback.message.edit_text(
        "❓ <b>GUSTO Support</b>

"
        "Если нужна помощь:
"
        "• Пишите: @gusto_support
"
        "• Или напишите сюда сообщение

"
        "<i>GUSTO — Быстрый. Безопасный. Без границ.</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📨 Написать @gusto_support", url=f"https://t.me/{SUPPORT_USERNAME}")],
            [InlineKeyboardButton(text="✏️ Написать сюда", callback_data="write_support")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="main")]
        ])
    )

@dp.callback_query(F.data == "write_support")
async def cb_write_support(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SupportFlow.write_message)
    await callback.message.edit_text(
        "✏️ <b>Напишите ваше сообщение:</b>

"
        "Опишите проблему или вопрос.
"
        "Мы ответим в ближайшее время.",
        reply_markup=back_kb("support")
    )

@dp.message(SupportFlow.write_message)
async def support_message(message: Message, state: FSMContext):
    user = await backend.get_user(message.from_user.id)

    support_text = (
        f"📩 <b>Новое обращение</b>

"
        f"От: {message.from_user.full_name} (@{message.from_user.username or 'N/A'})
"
        f"ID: <code>{message.from_user.id}</code>
"
        f"User ID: {user['id'] if user and not user.get('error') else 'N/A'}

"
        f"Сообщение:
{message.text}"
    )

    # Send to all admins
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, support_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Failed to send support message to admin {admin_id}: {e}")

    await message.answer(
        "✅ <b>Сообщение отправлено!</b>

"
        "Мы ответим вам в ближайшее время.
"
        "Обычно ответ занимает до 2 часов.",
        reply_markup=main_menu_kb()
    )
    await state.clear()

# ==================== ADMIN PANEL ====================

@dp.callback_query(F.data == "admin")
async def cb_admin(callback: CallbackQuery, state: FSMContext):
    user = await backend.get_user(callback.from_user.id)
    if not user or not user.get("is_admin", False):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    await state.set_state(AdminFlow.select_action)

    await callback.message.edit_text(
        "🔧 <b>Админ-панель GUSTO</b>

"
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

@dp.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    user = await backend.get_user(callback.from_user.id)
    if not user or not user.get("is_admin", False):
        return

    # Get stats from backend
    stats = await backend._request("GET", "/api/admin/dashboard")

    if stats and not stats.get("error"):
        await callback.message.edit_text(
            f"📊 <b>Статистика GUSTO</b>

"
            f"👥 Пользователей: <b>{stats.get('users', 0)}</b>
"
            f"📡 Серверов: <b>{stats.get('servers', 0)}</b>
"
            f"💰 Выручка: <b>{stats.get('revenue', 0):.2f}₽</b>
"
            f"🟢 Активных подписок: <b>{stats.get('active_subscriptions', 0)}</b>

"
            f"<i>Обновлено: {datetime.now().strftime('%H:%M:%S')}</i>",
            reply_markup=back_kb("admin")
        )
    else:
        await callback.answer("❌ Ошибка загрузки статистики", show_alert=True)

@dp.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    user = await backend.get_user(callback.from_user.id)
    if not user or not user.get("is_admin", False):
        return

    await state.set_state(AdminFlow.broadcast_message)
    await callback.message.edit_text(
        "📢 <b>Массовая рассылка</b>

"
        "Введите сообщение для отправки всем пользователям:

"
        "<i>Поддерживается HTML-разметка</i>",
        reply_markup=back_kb("admin")
    )

@dp.message(AdminFlow.broadcast_message)
async def admin_broadcast_message(message: Message, state: FSMContext):
    user = await backend.get_user(message.from_user.id)
    if not user or not user.get("is_admin", False):
        await state.clear()
        return

    broadcast_text = message.text

    # Get all users
    users = await backend._request("GET", "/api/users/")
    if not users or users.get("error"):
        await message.answer("❌ Ошибка получения списка пользователей")
        return

    sent = 0
    failed = 0

    await message.answer("⏳ Рассылка началась...")

    for u in users:
        try:
            await bot.send_message(u["telegram_id"], broadcast_text, parse_mode=ParseMode.HTML)
            sent += 1
        except:
            failed += 1

        if (sent + failed) % 30 == 0:
            await asyncio.sleep(1)

    await message.answer(
        f"✅ <b>Рассылка завершена!</b>

"
        f"📤 Отправлено: {sent}
"
        f"❌ Ошибок: {failed}",
        reply_markup=main_menu_kb(is_admin=True)
    )
    await state.clear()

# ==================== BACK TO MAIN ====================

@dp.callback_query(F.data == "main")
async def cb_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    user = await backend.get_user(callback.from_user.id)
    is_admin = user.get("is_admin", False) if user and not user.get("error") else False

    await callback.message.edit_text(
        "🚀 <b>GUSTO VPN</b>

"
        "Выберите действие 👇",
        reply_markup=main_menu_kb(is_admin)
    )

# ==================== MAIN ====================

async def main():
    logger.info("🚀 GUSTO Bot starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
