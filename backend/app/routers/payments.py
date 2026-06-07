from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import GustoPayment

router = APIRouter()


@router.get("/")
async def list_payments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GustoPayment))
    return result.scalars().all()


@router.post("/webhook/cryptobot")
async def cryptobot_webhook(data: dict, db: AsyncSession = Depends(get_db)):
    # Обработка webhook от CryptoBot
    return {"status": "processed"}


@router.post("/webhook/yookassa")
async def yookassa_webhook(data: dict, db: AsyncSession = Depends(get_db)):
    # Обработка webhook от YooKassa
    return {"status": "processed"}
