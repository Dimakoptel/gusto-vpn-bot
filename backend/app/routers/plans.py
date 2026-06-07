"""Plans Router — CRUD + seed default plans"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.database import get_db
from app.models.plan import GustoPlan, PlanDuration
from app.dependencies import get_current_admin

router = APIRouter(prefix="/api/plans", tags=["Plans"])

async def seed_default_plans(db: AsyncSession) -> dict:
    """Seed 5 default plans if table is empty"""
    result = await db.execute(select(GustoPlan))
    existing = result.scalars().all()

    if existing:
        return {"total": len(existing), "seeded": False, "message": "Plans already exist"}

    plans = [
        GustoPlan(
            name="start",
            display_name="🌱 GUSTO Start",
            description="Базовый тариф для начинающих",
            price=199,
            duration_days=30,
            traffic_gb=100,
            speed_mbps=100,
            device_limit=3,
            ip_limit=3,
            protocol="vless",
            security="reality",
            is_active=True,
            is_premium=False,
            is_popular=False,
            sort_order=1
        ),
        GustoPlan(
            name="pro",
            display_name="⚡ GUSTO Про",
            description="Оптимальный выбор для большинства",
            price=399,
            duration_days=30,
            traffic_gb=500,
            speed_mbps=500,
            device_limit=5,
            ip_limit=5,
            protocol="vless",
            security="reality",
            is_active=True,
            is_premium=False,
            is_popular=True,
            sort_order=2
        ),
        GustoPlan(
            name="ultra",
            display_name="🔥 GUSTO Ultra",
            description="Максимум скорости и трафика",
            price=699,
            duration_days=30,
            traffic_gb=1000,
            speed_mbps=1000,
            device_limit=5,
            ip_limit=5,
            protocol="vless",
            security="reality",
            is_active=True,
            is_premium=True,
            is_popular=False,
            sort_order=3
        ),
        GustoPlan(
            name="3months",
            display_name="📅 GUSTO 3 месяца",
            description="Экономия 20% за квартал",
            price=999,
            duration_days=90,
            traffic_gb=1500,
            speed_mbps=500,
            device_limit=5,
            ip_limit=5,
            protocol="vless",
            security="reality",
            is_active=True,
            is_premium=False,
            is_popular=False,
            sort_order=4
        ),
        GustoPlan(
            name="year",
            display_name="🏆 GUSTO 1 год",
            description="Максимальная экономия — 40%",
            price=2999,
            duration_days=365,
            traffic_gb=5000,
            speed_mbps=1000,
            device_limit=5,
            ip_limit=5,
            protocol="vless",
            security="reality",
            is_active=True,
            is_premium=True,
            is_popular=False,
            sort_order=5
        ),
    ]

    for plan in plans:
        db.add(plan)

    await db.commit()
    return {"total": len(plans), "seeded": True, "message": "Default plans created"}

@router.post("/seed")
async def seed_plans(
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Seed default plans (admin only)"""
    result = await seed_default_plans(db)
    return result

@router.get("/")
async def list_plans(
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all plans (public)"""
    query = select(GustoPlan).order_by(GustoPlan.sort_order)
    if is_active is not None:
        query = query.where(GustoPlan.is_active == is_active)

    result = await db.execute(query)
    plans = result.scalars().all()
    return plans

@router.get("/{plan_id}")
async def get_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get plan by ID (public)"""
    plan = await db.get(GustoPlan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    return plan

@router.post("/")
async def create_plan(
    data: dict,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Create new plan (admin only)"""
    plan = GustoPlan(**data)
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan

@router.put("/{plan_id}")
async def update_plan(
    plan_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Update plan (admin only)"""
    plan = await db.get(GustoPlan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")

    for key, value in data.items():
        if hasattr(plan, key):
            setattr(plan, key, value)

    await db.commit()
    await db.refresh(plan)
    return plan

@router.delete("/{plan_id}")
async def delete_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Delete plan (admin only)"""
    plan = await db.get(GustoPlan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")

    await db.delete(plan)
    await db.commit()
    return {"deleted": True}
