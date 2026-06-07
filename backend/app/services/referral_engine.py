"""GUSTO Referral Engine — 3-уровневая система + ачивки"""
from decimal import Decimal
from typing import Optional, List, Dict
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.user import GustoUser
from app.models.payment import GustoPayment
from app.config import settings


class GustoReferralEngine:
    """GUSTO Партнерская программа"""

    LEVELS = settings.REFERRAL_LEVELS

    ACHIEVEMENTS = {
        "first_ref": {"name": "🌱 Первый друг", "desc": "Пригласите 1 друга", "reward": 0},
        "10_refs": {"name": "🤝 Лидер мнений", "desc": "10 рефералов", "reward": 500},
        "50_refs": {"name": "👑 GUSTO Ambassador", "desc": "50 рефералов", "reward": 5000},
        "100gb": {"name": "🌊 Мореход", "desc": "100GB трафика", "reward": 0},
        "1tb": {"name": "🚀 Космонавт", "desc": "1TB трафика", "reward": 300},
        "1year": {"name": "💎 Ветеран", "desc": "1 год с GUSTO", "reward": 1000},
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_chain(self, user_id: int, depth: int = 3) -> List[GustoUser]:
        chain = []
        current_id = user_id

        for _ in range(depth):
            result = await self.db.execute(select(GustoUser).where(GustoUser.id == current_id))
            user = result.scalar_one_or_none()

            if not user or not user.referred_by:
                break

            result = await self.db.execute(select(GustoUser).where(GustoUser.id == user.referred_by))
            referrer = result.scalar_one_or_none()

            if referrer:
                chain.append(referrer)
                current_id = referrer.id
            else:
                break

        return chain

    async def process_payment(self, payment: GustoPayment) -> Dict:
        if payment.referral_processed or payment.status != "success":
            return {"distributed": False, "commissions": []}

        result = await self.db.execute(select(GustoUser).where(GustoUser.id == payment.user_id))
        user = result.scalar_one_or_none()

        if not user or not user.referred_by:
            payment.referral_processed = True
            return {"distributed": False, "commissions": []}

        chain = await self.get_chain(user.id, depth=3)
        commissions = []

        for level, referrer in enumerate(chain, 1):
            if level > 3:
                break

            rate = Decimal(str(self.LEVELS.get(level, 0)))
            commission = payment.amount * rate

            referrer.referral_balance += commission
            referrer.total_earned += commission

            ref_count = await self._get_referral_count(referrer.id)
            referrer.referral_level = self._calculate_level(ref_count)

            commissions.append({
                "referrer_id": referrer.id,
                "telegram_id": referrer.telegram_id,
                "level": level,
                "amount": commission,
                "rate": float(rate)
            })

            await self._check_achievements(referrer)

        payment.referral_processed = True
        return {"distributed": True, "commissions": commissions}

    async def _get_referral_count(self, user_id: int) -> int:
        result = await self.db.execute(
            select(func.count(GustoUser.id)).where(GustoUser.referred_by == user_id)
        )
        return result.scalar() or 0

    def _calculate_level(self, count: int) -> int:
        if count >= 50: return 5
        if count >= 20: return 4
        if count >= 10: return 3
        if count >= 5: return 2
        if count >= 1: return 1
        return 0

    async def _check_achievements(self, user: GustoUser):
        new_achievements = []
        current = set(user.achievements or [])
        ref_count = await self._get_referral_count(user.id)

        checks = {
            "first_ref": ref_count >= 1,
            "10_refs": ref_count >= 10,
            "50_refs": ref_count >= 50,
        }

        for ach_id, condition in checks.items():
            if condition and ach_id not in current:
                new_achievements.append(ach_id)
                ach = self.ACHIEVEMENTS[ach_id]
                if ach["reward"] > 0:
                    user.referral_balance += Decimal(str(ach["reward"]))

        if new_achievements:
            user.achievements = list(current | set(new_achievements))

    async def withdraw(self, user_id: int, amount: Optional[Decimal] = None) -> Dict:
        result = await self.db.execute(select(GustoUser).where(GustoUser.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            return {"success": False, "error": "User not found"}

        if user.referral_balance < settings.REFERRAL_MIN_WITHDRAW:
            return {
                "success": False,
                "error": f"Минимум для вывода: {settings.REFERRAL_MIN_WITHDRAW}₽",
                "balance": float(user.referral_balance)
            }

        withdraw_amount = amount or user.referral_balance
        if withdraw_amount > user.referral_balance:
            return {"success": False, "error": "Недостаточно средств"}

        user.referral_balance -= withdraw_amount
        return {"success": True, "amount": float(withdraw_amount), "remaining": float(user.referral_balance)}
