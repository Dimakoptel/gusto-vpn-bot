"""Notification Service — отправка уведомлений в Telegram"""
import logging
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import GustoUser
from app.models.server import GustoServer

logger = logging.getLogger("gusto.notifications")

class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_bot(self):
        """Получить экземпляр бота (singleton)"""
        # In production, this should be injected or use a singleton
        from aiogram import Bot
        import os
        token = os.getenv("BOT_TOKEN", "")
        if not token:
            return None
        return Bot(token=token)

    async def _send(self, telegram_id: int, text: str, parse_mode: str = "HTML") -> bool:
        """Отправить сообщение пользователю"""
        try:
            bot = await self._get_bot()
            if not bot:
                logger.error("❌ Bot not available for notification")
                return False
            await bot.send_message(telegram_id, text, parse_mode=parse_mode)
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send notification to {telegram_id}: {e}")
            return False

    async def _send_to_admins(self, text: str, parse_mode: str = "HTML") -> None:
        """Отправить всем админам"""
        from app.services.config_service import ConfigService
        admin_ids = await ConfigService.get("ADMIN_IDS")
        if not admin_ids:
            return

        for admin_id in admin_ids:
            await self._send(admin_id, text, parse_mode)

    # === User Notifications ===

    async def payment_success(self, user_id: int, amount: float, plan_name: str, 
                              config_link: str = None, server_name: str = None) -> None:
        """Уведомление об успешной оплате"""
        result = await self.db.execute(select(GustoUser).where(GustoUser.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return

        text = (
            f"🎉 <b>Оплата успешна!</b>\n\n"
            f"💰 Сумма: <b>{amount:.0f}₽</b>\n"
            f"📦 Тариф: <b>{plan_name}</b>\n"
        )
        if server_name:
            text += f"🌍 Сервер: <b>{server_name}</b>\n"
        text += "\n✅ Ваша подписка активирована!"

        await self._send(user.telegram_id, text)

    async def payment_failed(self, user_id: int, amount: float, reason: str) -> None:
        """Уведомление о неудачной оплате"""
        result = await self.db.execute(select(GustoUser).where(GustoUser.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return

        await self._send(user.telegram_id, (
            f"❌ <b>Оплата не удалась</b>\n\n"
            f"💰 Сумма: {amount:.0f}₽\n"
            f"Причина: {reason}\n\n"
            f"Попробуйте снова или обратитесь в поддержку."
        ))

    async def subscription_activated(self, user_id: int, plan_name: str, 
                                     expires_at: str, config_link: str) -> None:
        """Подписка активирована"""
        result = await self.db.execute(select(GustoUser).where(GustoUser.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return

        await self._send(user.telegram_id, (
            f"✅ <b>Подписка активирована!</b>\n\n"
            f"📦 Тариф: {plan_name}\n"
            f"📅 Действует до: {expires_at[:10] if len(expires_at) > 10 else expires_at}\n\n"
            f"🔑 <b>Ваша конфигурация:</b>\n"
            f"<code>{config_link}</code>\n\n"
            f"Скопируйте и вставьте в приложение V2RayNG/Streisand!"
        ))

    async def subscription_expiring_soon(self, user_id: int, email: str, days: int) -> None:
        """Подписка истекает скоро"""
        result = await self.db.execute(select(GustoUser).where(GustoUser.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return

        emoji = "⚠️" if days == 1 else "⏰"
        await self._send(user.telegram_id, (
            f"{emoji} <b>Подписка истекает через {days} {'день' if days == 1 else 'дня'}!</b>\n\n"
            f"📧 Email: <code>{email}</code>\n\n"
            f"Продлите в разделе 'Мой кабинет' → 'Продлить'"
        ))

    async def subscription_expired(self, user_id: int, email: str) -> None:
        """Подписка истекла"""
        result = await self.db.execute(select(GustoUser).where(GustoUser.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return

        await self._send(user.telegram_id, (
            f"🔴 <b>Подписка истекла!</b>\n\n"
            f"📧 Email: <code>{email}</code>\n\n"
            f"Купите новую подписку в главном меню!"
        ))

    async def low_traffic(self, user_id: int, email: str, remaining_gb: float) -> None:
        """Заканчивается трафик"""
        result = await self.db.execute(select(GustoUser).where(GustoUser.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return

        await self._send(user.telegram_id, (
            f"⚠️ <b>Заканчивается трафик!</b>\n\n"
            f"📧 Email: <code>{email}</code>\n"
            f"📊 Осталось: <b>{remaining_gb:.1f} GB</b>\n\n"
            f"Продлите подписку для добавления трафика!"
        ))

    async def config_sharing_detected(self, user_id: int, email: str, 
                                       ips: List[str], countries: List[str]) -> None:
        """Обнаружен sharing конфига"""
        result = await self.db.execute(select(GustoUser).where(GustoUser.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return

        await self._send(user.telegram_id, (
            f"🚫 <b>Обнаружено нарушение!</b>\n\n"
            f"📧 Email: <code>{email}</code>\n"
            f"🌍 Страны: {', '.join(countries)}\n"
            f"📡 IP: {len(ips)} адресов\n\n"
            f"Ваш конфиг используется слишком многими устройствами.\n"
            f"Подписка временно ограничена. Обратитесь в поддержку."
        ))

    async def referral_earned(self, user_id: int, amount: float, level: int, 
                              from_user: int) -> None:
        """Реферальное начисление"""
        result = await self.db.execute(select(GustoUser).where(GustoUser.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return

        levels = ["🥇", "🥈", "🥉"]
        await self._send(user.telegram_id, (
            f"💰 <b>Реферальное начисление!</b>\n\n"
            f"{levels[level-1]} Уровень {level}: <b>+{amount:.2f}₽</b>\n"
            f"От пользователя: #{from_user}\n\n"
            f"Текущий баланс: {float(user.referral_balance):.2f}₽"
        ))

    async def referral_payout(self, user_id: int, amount: float) -> None:
        """Выплата реферальных"""
        result = await self.db.execute(select(GustoUser).where(GustoUser.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return

        await self._send(user.telegram_id, (
            f"💸 <b>Выплата реферальных!</b>\n\n"
            f"Сумма: <b>{amount:.2f}₽</b>\n"
            f"Проверьте ваш кошелек."
        ))

    # === Admin Notifications ===

    async def admin_new_payment(self, user_id: int, amount: float, 
                                provider: str, plan_name: str) -> None:
        """Новый платеж — уведомить админов"""
        await self._send_to_admins(
            f"💰 <b>Новый платеж!</b>\n\n"
            f"Пользователь: #{user_id}\n"
            f"Сумма: {amount:.0f}₽\n"
            f"Провайдер: {provider}\n"
            f"Тариф: {plan_name}"
        )

    async def admin_server_offline(self, server_name: str, host: str, 
                                    error: str) -> None:
        """Сервер недоступен — уведомить админов"""
        await self._send_to_admins(
            f"🔴 <b>Сервер недоступен!</b>\n\n"
            f"Имя: {server_name}\n"
            f"Хост: {host}\n"
            f"Ошибка: {error}\n\n"
            f"Проверьте сервер срочно!"
        )

    async def admin_new_user(self, user_id: int, telegram_id: int, 
                             username: str) -> None:
        """Новый пользователь — уведомить админов"""
        await self._send_to_admins(
            f"👤 <b>Новый пользователь!</b>\n\n"
            f"ID: #{user_id}\n"
            f"Telegram: {telegram_id}\n"
            f"Username: @{username or 'N/A'}"
        )

    async def admin_fraud_detected(self, user_id: int, email: str, 
                                    reason: str) -> None:
        """Обнаружен фрод — уведомить админов"""
        await self._send_to_admins(
            f"🚫 <b>Обнаружен фрод!</b>\n\n"
            f"Пользователь: #{user_id}\n"
            f"Email: {email}\n"
            f"Причина: {reason}"
        )

    async def broadcast(self, text: str, target_users: Optional[List[int]] = None) -> dict:
        """Массовая рассылка (rate limited externally)"""
        if target_users:
            users = target_users
        else:
            result = await self.db.execute(select(GustoUser))
            users = [u.telegram_id for u in result.scalars().all()]

        sent = 0
        failed = 0
        for tg_id in users:
            if await self._send(tg_id, text):
                sent += 1
            else:
                failed += 1

        return {"sent": sent, "failed": failed, "total": len(users)}
