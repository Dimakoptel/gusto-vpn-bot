"""Servers Router"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.server import GustoServer

router = APIRouter(prefix="/api/servers", tags=["Servers"])

@router.get("/")
async def list_servers(db: AsyncSession = Depends(get_db)):
    """List all servers"""
    result = await db.execute(select(GustoServer))
    return result.scalars().all()

@router.get("/{server_id}")
async def get_server(server_id: int, db: AsyncSession = Depends(get_db)):
    """Get server by ID"""
    server = await db.get(GustoServer, server_id)
    if not server:
        raise HTTPException(404, "Server not found")
    return server
