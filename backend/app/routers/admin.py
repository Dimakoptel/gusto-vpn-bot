"""Admin Router — Dashboard stats"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import GustoUser
from app.models.subscription import GustoSubscription, SubscriptionStatus
from app.models.payment import GustoPayment, PaymentStatus
from app.models.server import GustoServer

router = APIRouter(prefix="/api/admin", tags=["Admin"])

@router.get("/dashboard")
async def dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Dashboard statistics"""
    # Total users
    user_result = await db.execute(select(func.count(GustoUser.id)))
    total_users = user_result.scalar()

    # Active subscriptions
    sub_result = await db.execute(
        select(func.count(GustoSubscription.id))
        .where(GustoSubscription.status == SubscriptionStatus.ACTIVE)
    )
    active_subs = sub_result.scalar()

    # Total revenue
    revenue_result = await db.execute(
        select(func.sum(GustoPayment.amount))
        .where(GustoPayment.status == PaymentStatus.SUCCESS)
    )
    total_revenue = revenue_result.scalar() or 0

    # Today's revenue
    today = datetime.utcnow().date()
    today_revenue_result = await db.execute(
        select(func.sum(GustoPayment.amount))
        .where(
            GustoPayment.status == PaymentStatus.SUCCESS,
            GustoPayment.paid_at >= today
        )
    )
    today_revenue = today_revenue_result.scalar() or 0

    # Online servers
    server_result = await db.execute(
        select(func.count(GustoServer.id))
        .where(GustoServer.is_online == True)
    )
    online_servers = server_result.scalar()

    return {
        "total_users": total_users,
        "active_subscriptions": active_subs,
        "total_revenue": float(total_revenue),
        "today_revenue": float(today_revenue),
        "online_servers": online_servers,
        "timestamp": datetime.utcnow().isoformat()
    }
