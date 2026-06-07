"""Referrals Router"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.user import GustoUser

router = APIRouter(prefix="/api/referrals", tags=["Referrals"])

@router.get("/stats/{user_id}")
async def get_referral_stats(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get referral stats for user"""
    result = await db.execute(select(GustoUser).where(GustoUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return {"error": "User not found"}

    # Count referrals
    ref_result = await db.execute(
        select(func.count(GustoUser.id)).where(GustoUser.referred_by == user_id)
    )
    total_referrals = ref_result.scalar()

    return {
        "total_referrals": total_referrals,
        "total_earned": float(user.total_earned),
        "referral_balance": float(user.referral_balance),
        "level": user.referral_level
    }
