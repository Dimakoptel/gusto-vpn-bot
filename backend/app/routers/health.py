"""Health Check Router"""
from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_db, engine
from app.models.user import GustoUser

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("/")
async def health_check():
    """Публичный health check"""
    return {
        "status": "healthy",
        "service": "gusto-backend",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/db")
async def db_health_check(db: AsyncSession = Depends(get_db)):
    """Проверка подключения к БД"""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except SQLAlchemyError as e:
        return {"status": "unhealthy", "database": str(e)}
