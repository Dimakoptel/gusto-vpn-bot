"""Dependencies — JWT auth, admin check"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.config import core_settings
from app.models.user import GustoUser

security = HTTPBearer()

async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Проверить JWT токен и вернуть админа"""
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token, 
            core_settings.SECRET_KEY, 
            algorithms=[core_settings.ALGORITHM]
        )
        user_id = int(payload.get("sub"))
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(GustoUser).where(GustoUser.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    return user

async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Опциональная проверка токена (для публичных endpoints)"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, core_settings.SECRET_KEY, algorithms=[core_settings.ALGORITHM])
        user_id = int(payload.get("sub"))
        result = await db.execute(select(GustoUser).where(GustoUser.id == user_id))
        return result.scalar_one_or_none()
    except Exception:
        return None
