"""Users Router"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import GustoUser

router = APIRouter(prefix="/api/users", tags=["Users"])

@router.post("/")
async def create_user(data: dict, db: AsyncSession = Depends(get_db)):
    """Create new user"""
    user = GustoUser(
        telegram_id=data.get("telegram_id"),
        username=data.get("username"),
        first_name=data.get("first_name"),
        last_name=data.get("last_name"),
        referred_by=data.get("referred_by"),
        country_code=data.get("country_code", "RU"),
        language=data.get("language", "ru")
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.get("/telegram/{telegram_id}")
async def get_user_by_telegram(telegram_id: int, db: AsyncSession = Depends(get_db)):
    """Get user by Telegram ID"""
    result = await db.execute(select(GustoUser).where(GustoUser.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    return user

@router.get("/")
async def list_users(db: AsyncSession = Depends(get_db)):
    """List all users"""
    result = await db.execute(select(GustoUser))
    return result.scalars().all()
