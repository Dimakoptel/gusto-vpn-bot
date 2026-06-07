from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models import GustoUser

router = APIRouter()


@router.get("/")
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GustoUser))
    return result.scalars().all()


@router.get("/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GustoUser).where(GustoUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/")
async def create_user(data: dict, db: AsyncSession = Depends(get_db)):
    user = GustoUser(**data)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/{user_id}/ban")
async def ban_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GustoUser).where(GustoUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_banned = True
    await db.commit()
    return {"status": "banned"}
