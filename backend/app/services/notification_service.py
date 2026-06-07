"""Notification Service — использует динамические настройки из БД"""
import asyncio
from typing import Optional, List
from datetime import datetime

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.services.config_service import get_config, get_configs


class NotificationService:
    """Отправка уведомлений в Telegram с динамическими настройками"""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def _get_support_username(self) -> str:
        return await get_config("SUPPORT_USERNAME", "gusto_support")

    async def _get_support_link(self) -> str:
        link = await get_config("SUPPORT_LINK", "")
        if link:
            return link
        username = await self._get_support_username()
        return f"https://t.me/{username}" if username else ""

    async def _get_brand_name(self) -> str:
        return await get_config("BRAND_NAME", "GUSTO VPN")

    async def _should_notify(self, key: str) -> bool:
        return await get_config(key, True)

    def _support_keyboard(self, support_link: str) -> Optional[InlineKeyboardMarkup]:
        if not support_link:
            return None
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🆘 Поддержка", url=support_link)]
        ])

    # ========== USER NOTIFICATIONS ==========

    async def payment_success(self, user_id: int, amount: float, currency: str, subscription_info: str):
        if not await self._should_notify("NOTIFY_PAYMENT_SUCCESS"):
            return

        brand = await self._get_brand_name()
        support_link = await self._get_support_link()

        text = (
            f"✅ <b>Оплата прошла успешно!</b>\n\n"
            f"💰 Сумма: <code>{amount} {currency}</code>\n"
            f"📦 Подписка: {subscription_info}\n\n"
            f"Спасибо за доверие к {brand}! 🚀"
        )

        await self.bot.send_message(
            user_id, text,
            parse_mode="HTML",
            reply_markup=self._support_keyboard(support_link)
        )

    async def payment_failed(self, user_id: int, amount: float, reason: str):
        if not await self._should_notify("NOTIFY_PAYMENT_FAILED"):
            return

        brand = await self._get_brand_name()
        support_link = await self._get_support_link()

        text = (
            f"❌ <b>Оплата не удалась</b>\n\n"
            f"💰 Сумма: <code>{amount}</code>\n"
            f"Причина: {reason}\n\n"
            f"Попробуйте ещё раз или обратитесь в поддержку {brand}."
        )

        await self.bot.send_message(
            user_id, text,
            parse_mode="HTML",
            reply_markup=self._support_keyboard(support_link)
        )

    async def subscription_expiring_soon(self, user_id: int, days_left: int, sub_info: str):
        brand = await self._get_brand_name()
        support_link = await self._get_support_link()

        text = (
            f"⏰ <b>Подписка истекает через {days_left} {self._plural_days(days_left)}!</b>\n\n"
            f"📦 {sub_info}\n\n"
            f"Не забудьте продлить, чтобы оставаться на связи с {brand}. 🌐"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Продлить", callback_data="renew_subscription")],
            [InlineKeyboardButton(text="🆘 Поддержка", url=support_link)] if support_link else []
        ])

        await self.bot.send_message(user_id, text, parse_mode="HTML", reply_markup=keyboard)

    async def subscription_expired(self, user_id: int, sub_info: str):
        brand = await self._get_brand_name()
        support_link = await self._get_support_link()

        text = (
            f"🔴 <b>Подписка истекла</b>\n\n"
            f"📦 {sub_info}\n\n"
            f"Ваш доступ к {brand} приостановлен. Продлите подписку, чтобы возобновить доступ."
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Продлить", callback_data="buy_subscription")],
            [InlineKeyboardButton(text="🆘 Поддержка", url=support_link)] if support_link else []
        ])

        await self.bot.send_message(user_id, text, parse_mode="HTML", reply_markup=keyboard)

    async def low_traffic(self, user_id: int, remaining_gb: float, total_gb: float):
        threshold = await get_config("LOW_TRAFFIC_THRESHOLD_GB", 5.0)
        if remaining_gb > threshold:
            return

        brand = await self._get_brand_name()
        support_link = await self._get_support_link()

        text = (
            f"⚠️ <b>Заканчивается трафик</b>\n\n"
            f"📊 Осталось: <code>{remaining_gb:.1f} GB</code> из {total_gb} GB\n\n"
            f"Рекомендуем продлить или обновить тариф {brand}."
        )

        await self.bot.send_message(
            user_id, text,
            parse_mode="HTML",
            reply_markup=self._support_keyboard(support_link)
        )

    async def config_sharing_detected(self, user_id: int, ip_count: int, action: str):
        brand = await self._get_brand_name()

        text = (
            f"🚨 <b>Обнаружено подозрительная активность</b>\n\n"
            f"Ваш конфиг используется с {ip_count} разных IP-адресов.\n"
            f"Действие: <b>{action}</b>\n\n"
            f"Если это не вы — срочно обратитесь в поддержку {brand}."
        )

        await self.bot.send_message(user_id, text, parse_mode="HTML")

    async def referral_reward(self, user_id: int, level: int, amount: float, from_user: str):
        brand = await self._get_brand_name()

        text = (
            f"🎉 <b>Реферальное вознаграждение!</b>\n\n"
            f"Уровень {level}: +<code>{amount}</code> руб.\n"
            f"От пользователя: {from_user}\n\n"
            f"Продолжайте приглашать друзей в {brand}! 💪"
        )

        await self.bot.send_message(user_id, text, parse_mode="HTML")

    async def welcome_message(self, user_id: int, referral_code: Optional[str] = None):
        welcome = await get_config("WELCOME_MESSAGE", "Добро пожаловать в GUSTO VPN! 🚀")
        brand = await self._get_brand_name()
        support_link = await self._get_support_link()

        text = f"{welcome}\n\n"
        if referral_code:
            text += f"Ваш реферальный код: <code>{referral_code}</code>\n\n"
        text += f"Используйте меню ниже для управления подпиской {brand}."

        await self.bot.send_message(
            user_id, text,
            parse_mode="HTML",
            reply_markup=self._support_keyboard(support_link)
        )

    # ========== ADMIN NOTIFICATIONS ==========

    async def admin_new_payment(self, admin_ids: List[int], user_id: int, amount: float, provider: str):
        brand = await self._get_brand_name()

        text = (
            f"💰 <b>Новая оплата в {brand}</b>\n\n"
            f"Пользователь: <code>{user_id}</code>\n"
            f"Сумма: <code>{amount}</code>\n"
            f"Провайдер: {provider}\n"
            f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        for admin_id in admin_ids:
            try:
                await self.bot.send_message(admin_id, text, parse_mode="HTML")
            except Exception:
                pass

    async def admin_server_offline(self, admin_ids: List[int], server_name: str, reason: str):
        if not await self._should_notify("NOTIFY_SERVER_OFFLINE"):
            return

        brand = await self._get_brand_name()

        text = (
            f"🔴 <b>Сервер недоступен — {brand}</b>\n\n"
            f"🖥 {server_name}\n"
            f"Причина: {reason}\n"
            f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"Требуется проверка!"
        )

        for admin_id in admin_ids:
            try:
                await self.bot.send_message(admin_id, text, parse_mode="HTML")
            except Exception:
                pass

    async def admin_3xui_update(self, admin_ids: List[int], version: str, changes: str):
        text = (
            f"📦 <b>Доступно обновление 3x-ui</b>\n\n"
            f"Версия: <code>{version}</code>\n"
            f"Изменения:\n{changes}\n\n"
            f"Рекомендуется проверить совместимость API перед обновлением."
        )

        for admin_id in admin_ids:
            try:
                await self.bot.send_message(admin_id, text, parse_mode="HTML")
            except Exception:
                pass

    async def broadcast(self, user_ids: List[int], message: str, parse_mode: str = "HTML", 
                       keyboard: Optional[InlineKeyboardMarkup] = None, rate_limit: float = 0.05):
        """Массовая рассылка с rate limiting"""
        success = 0
        failed = 0

        for user_id in user_ids:
            try:
                await self.bot.send_message(user_id, message, parse_mode=parse_mode, reply_markup=keyboard)
                success += 1
                await asyncio.sleep(rate_limit)
            except Exception:
                failed += 1

        return {"sent": success, "failed": failed}

    @staticmethod
    def _plural_days(n: int) -> str:
        if n % 10 == 1 and n % 100 != 11:
            return "день"
        elif 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
            return "дня"
        else:
            return "дней"
