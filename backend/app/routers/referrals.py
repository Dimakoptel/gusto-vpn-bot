from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import GustoUser
from app.services import GustoReferralEngine

router = APIRouter()


@router.get("/stats/{user_id}")
async def referral_stats(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GustoUser).where(GustoUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    engine = GustoReferralEngine(db)
    ref_count = await engine._get_referral_count(user_id)

    return {
        "code": user.referral_code,
        "balance": float(user.referral_balance),
        "total_earned": float(user.total_earned),
        "level": user.referral_level,
        "referrals_count": ref_count,
        "link": f"https://t.me/gustovpn_bot?start=ref_{user.referral_code}"
    }


@router.post("/withdraw/{user_id}")
async def withdraw_referral(user_id: int, db: AsyncSession = Depends(get_db)):
    engine = GustoReferralEngine(db)
    result = await engine.withdraw(user_id)
    await db.commit()
    return result
