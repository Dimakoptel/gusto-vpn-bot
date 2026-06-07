"""GUSTO Shield — Anti-Fraud System"""
from datetime import datetime, timedelta
from typing import Dict, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.user import GustoUser
from app.models.payment import GustoPayment
from app.models.subscription import GustoSubscription
from app.config import settings


class GustoAntiFraud:
    """Система обнаружения мошенничества"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_payment(self, user_id: int, amount: float) -> Dict:
        risk_score = 0.0
        reasons = []

        hour_ago = datetime.utcnow() - timedelta(hours=1)
        payments_count = await self.db.execute(
            select(func.count(GustoPayment.id)).where(
                GustoPayment.user_id == user_id,
                GustoPayment.created_at >= hour_ago
            )
        )
        recent_payments = payments_count.scalar()

        if recent_payments > settings.MAX_PAYMENTS_PER_HOUR:
            risk_score += 0.4
            reasons.append("Слишком много платежей за час")

        if amount > 10000:
            risk_score += 0.2
            reasons.append("Крупная сумма")

        return {
            "allowed": risk_score < 0.7,
            "reason": "; ".join(reasons) if reasons else "OK",
            "risk_score": min(risk_score, 1.0)
        }

    async def check_config_sharing(self, user_id: int) -> Dict:
        from app.services.x3ui_client import GustoX3UIClient, X3UIPanel

        result = await self.db.execute(
            select(GustoUser).where(GustoUser.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return {"is_sharing": False, "unique_ips": 0, "action": "none"}

        subs_result = await self.db.execute(
            select(GustoSubscription).where(
                GustoSubscription.user_id == user_id,
                GustoSubscription.status == "active"
            )
        )
        subscriptions = subs_result.scalars().all()

        unique_ips = set()
        for sub in subscriptions:
            if sub.server:
                client = GustoX3UIClient(X3UIPanel(
                    host=sub.server.host,
                    port=sub.server.port,
                    username=sub.server.panel_username,
                    password=sub.server.panel_password,
                    name=sub.server.name
                ))
                stats = await client.get_client_stats(sub.email)
                if stats:
                    unique_ips.update(stats.get("ips", []))
                await client.close()

        is_sharing = len(unique_ips) > settings.MAX_UNIQUE_IPS_PER_DAY
        action = "none"
        if is_sharing:
            action = "ban" if len(unique_ips) > 10 else "rotate"

        return {"is_sharing": is_sharing, "unique_ips": len(unique_ips), "action": action}
