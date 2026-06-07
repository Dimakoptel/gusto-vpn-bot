from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models import GustoServer

router = APIRouter()


@router.get("/")
async def list_servers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GustoServer))
    return result.scalars().all()


@router.post("/")
async def create_server(data: dict, db: AsyncSession = Depends(get_db)):
    server = GustoServer(**data)
    db.add(server)
    await db.commit()
    await db.refresh(server)
    return server


@router.get("/{server_id}/status")
async def server_status(server_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GustoServer).where(GustoServer.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return {"online": server.is_online, "cpu": server.cpu_load, "users": server.total_users}
