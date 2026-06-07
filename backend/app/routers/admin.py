from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import GustoUser, GustoServer, GustoPayment, GustoSubscription

router = APIRouter()


@router.get("/dashboard")
async def dashboard(db: AsyncSession = Depends(get_db)):
    users_count = await db.execute(select(func.count(GustoUser.id)))
    servers_count = await db.execute(select(func.count(GustoServer.id)))
    payments_sum = await db.execute(select(func.sum(GustoPayment.amount)))
    active_subs = await db.execute(
        select(func.count(GustoSubscription.id)).where(GustoSubscription.status == "active")
    )

    return {
        "users": users_count.scalar(),
        "servers": servers_count.scalar(),
        "revenue": float(payments_sum.scalar() or 0),
        "active_subscriptions": active_subs.scalar(),
        "brand": "GUSTO VPN",
        "tagline": "Быстрый. Безопасный. Без границ."
    }
