"""
GUSTO Notification Service — отправка уведомлений в Telegram
"""
import logging
from typing import Optional, List
from datetime import datetime, timedelta
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger("gusto.notifications")

class NotificationService:
    """Сервис уведомлений для пользователей бота"""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def send_notification(self, telegram_id: int, text: str, 
                                 reply_markup: Optional[InlineKeyboardMarkup] = None):
        """Отправить уведомление пользователю"""
        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
            logger.info(f"✅ Notification sent to {telegram_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send notification to {telegram_id}: {e}")
            return False

    # ==================== PAYMENT NOTIFICATIONS ====================

    async def payment_success(self, telegram_id: int, plan_name: str, 
                               amount: float, config_link: str):
        """Уведомление об успешной оплате + конфигурация"""
        text = (
            f"🎉 <b>Оплата успешна!</b>

"
            f"✅ Подписка <b>{plan_name}</b> активирована
"
            f"💰 Сумма: <b>{amount:.0f}₽</b>

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
            f"Вставьте ссылку в приложение и подключайтесь! 🚀"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Копировать конфиг", callback_data="copy_config")],
            [InlineKeyboardButton(text="📊 Мой кабинет", callback_data="account")]
        ])

        await self.send_notification(telegram_id, text, kb)

    async def payment_failed(self, telegram_id: int, amount: float, 
                              reason: str = "Ошибка платежа"):
        """Уведомление о неудачной оплате"""
        text = (
            f"❌ <b>Оплата не прошла</b>

"
            f"Сумма: <b>{amount:.0f}₽</b>
"
            f"Причина: {reason}

"
            f"Попробуйте снова или обратитесь в поддержку."
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="buy")],
            [InlineKeyboardButton(text="❓ Поддержка", callback_data="support")]
        ])

        await self.send_notification(telegram_id, text, kb)

    async def payment_pending(self, telegram_id: int, amount: float, 
                               pay_url: str, timeout_minutes: int = 30):
        """Уведомление об ожидании оплаты"""
        text = (
            f"⏳ <b>Ожидание оплаты</b>

"
            f"Сумма: <b>{amount:.0f}₽</b>
"
            f"У вас есть <b>{timeout_minutes} минут</b> для оплаты.

"
            f"После оплаты конфигурация придет автоматически."
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Перейти к оплате", url=pay_url)],
            [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data="check_payment")]
        ])

        await self.send_notification(telegram_id, text, kb)

    # ==================== SUBSCRIPTION NOTIFICATIONS ====================

    async def subscription_expiring_soon(self, telegram_id: int, days_left: int,
                                        plan_name: str, expiry_date: str):
        """Уведомление об истечении подписки (за 3/1 день)"""
        emoji = "⚠️" if days_left == 3 else "🚨"
        urgency = "скоро" if days_left == 3 else "<b>ЗАВТРА</b>"

        text = (
            f"{emoji} <b>Подписка истекает {urgency}!</b>

"
            f"📋 Тариф: <b>{plan_name}</b>
"
            f"📅 До: <b>{expiry_date}</b>
"
            f"⏳ Осталось: <b>{days_left} {'дня' if days_left == 3 else 'день'}</b>

"
            f"Продлите сейчас, чтобы не потерять доступ!"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Продлить", callback_data="renew")],
            [InlineKeyboardButton(text="📊 Мой кабинет", callback_data="account")]
        ])

        await self.send_notification(telegram_id, text, kb)

    async def subscription_expired(self, telegram_id: int, plan_name: str):
        """Уведомление об истечении подписки"""
        text = (
            f"🔴 <b>Подписка истекла</b>

"
            f"📋 Тариф: <b>{plan_name}</b>

"
            f"Ваш доступ к VPN приостановлен.
"
            f"Продлите подписку, чтобы возобновить доступ."
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Продлить", callback_data="renew")],
            [InlineKeyboardButton(text="🛒 Новая подписка", callback_data="buy")]
        ])

        await self.send_notification(telegram_id, text, kb)

    async def low_traffic(self, telegram_id: int, remaining_gb: float, 
                         total_gb: float, plan_name: str):
        """Уведомление о заканчивающемся трафике"""
        text = (
            f"📉 <b>Трафик заканчивается!</b>

"
            f"📋 Тариф: <b>{plan_name}</b>
"
            f"📊 Осталось: <b>{remaining_gb:.1f} GB</b> из {total_gb} GB

"
            f"Пополните трафик или продлите подписку."
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Продлить", callback_data="renew")],
            [InlineKeyboardButton(text="📊 Мой кабинет", callback_data="account")]
        ])

        await self.send_notification(telegram_id, text, kb)

    async def subscription_activated(self, telegram_id: int, plan_name: str,
                                      expiry_date: str, server_name: str):
        """Уведомление об активации подписки"""
        text = (
            f"✅ <b>Подписка активирована!</b>

"
            f"📋 Тариф: <b>{plan_name}</b>
"
            f"📡 Сервер: <b>{server_name}</b>
"
            f"📅 Действует до: <b>{expiry_date}</b>

"
            f"Получите конфигурацию в личном кабинете."
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔑 Получить конфиг", callback_data="config")],
            [InlineKeyboardButton(text="📊 Мой кабинет", callback_data="account")]
        ])

        await self.send_notification(telegram_id, text, kb)

    # ==================== REFERRAL NOTIFICATIONS ====================

    async def referral_earned(self, telegram_id: int, amount: float, 
                             level: int, referrer_name: str):
        """Уведомление о реферальном начислении"""
        text = (
            f"💰 <b>Реферальное начисление!</b>

"
            f"👤 {referrer_name} оплатил подписку
"
            f"🏆 Уровень: <b>{level}</b>
"
            f"💵 Начислено: <b>{amount:.2f}₽</b>

"
            f"Продолжайте приглашать друзей!"
        )

        await self.send_notification(telegram_id, text)

    async def achievement_unlocked(self, telegram_id: int, achievement_name: str,
                                    reward: float = 0):
        """Уведомление о разблокированном достижении"""
        text = (
            f"🏆 <b>Новое достижение!</b>

"
            f"🎉 <b>{achievement_name}</b>
"
        )
        if reward > 0:
            text += f"💰 Награда: <b>{reward:.0f}₽</b>

"
        text += "Продолжайте в том же духе!"

        await self.send_notification(telegram_id, text)

    # ==================== SECURITY NOTIFICATIONS ====================

    async def config_sharing_detected(self, telegram_id: int, unique_ips: int,
                                       action: str = "rotate"):
        """Уведомление об обнаружении sharing"""
        text = (
            f"🛡️ <b>GUSTO Shield: Обнаружена подозрительная активность</b>

"
            f"🔍 Обнаружено <b>{unique_ips}</b> уникальных IP
"
            f"⚠️ Возможно, конфигурация используется на нескольких устройствах

"
        )

        if action == "rotate":
            text += "🔑 Ваша конфигурация будет обновлена автоматически."
        elif action == "ban":
            text += "🔴 Подписка приостановлена. Обратитесь в поддержку."

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❓ Поддержка", callback_data="support")]
        ])

        await self.send_notification(telegram_id, text, kb)

    async def ip_changed(self, telegram_id: int, old_ip: str, new_ip: str):
        """Уведомление о смене IP (опционально)"""
        text = (
            f"📍 <b>Обнаружена смена IP</b>

"
            f"Старый: <code>{old_ip}</code>
"
            f"Новый: <code>{new_ip}</code>

"
            f"Если это не вы — обратитесь в поддержку."
        )

        await self.send_notification(telegram_id, text)

    # ==================== ADMIN NOTIFICATIONS ====================

    async def admin_new_payment(self, admin_id: int, user_id: int, 
                                 amount: float, plan_name: str):
        """Уведомление админу о новом платеже"""
        text = (
            f"💰 <b>Новый платеж!</b>

"
            f"👤 User ID: <code>{user_id}</code>
"
            f"📋 Тариф: {plan_name}
"
            f"💵 Сумма: <b>{amount:.0f}₽</b>
"
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

        await self.send_notification(admin_id, text)

    async def admin_server_offline(self, admin_id: int, server_name: str):
        """Уведомление админу о недоступном сервере"""
        text = (
            f"🔴 <b>Сервер недоступен!</b>

"
            f"📡 <b>{server_name}</b>
"
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}

"
            f"Проверьте сервер срочно!"
        )

        await self.send_notification(admin_id, text)

    async def admin_low_traffic_alert(self, admin_id: int, server_name: str,
                                       remaining_percent: float):
        """Уведомление админу о заканчивающемся трафике на сервере"""
        text = (
            f"⚠️ <b>Трафик на сервере заканчивается!</b>

"
            f"📡 <b>{server_name}</b>
"
            f"📊 Осталось: <b>{remaining_percent:.1f}%</b>

"
            f"Рассмотрите добавление трафика или новый сервер."
        )

        await self.send_notification(admin_id, text)

    # ==================== BROADCAST ====================

    async def broadcast(self, telegram_ids: List[int], text: str, 
                        reply_markup: Optional[InlineKeyboardMarkup] = None):
        """Массовая рассылка (с rate limiting)"""
        success = 0
        failed = 0

        for tg_id in telegram_ids:
            if await self.send_notification(tg_id, text, reply_markup):
                success += 1
            else:
                failed += 1

            # Rate limit: 30 messages/second
            if (success + failed) % 30 == 0:
                await asyncio.sleep(1)

        logger.info(f"Broadcast: {success} sent, {failed} failed")
        return {"sent": success, "failed": failed}
