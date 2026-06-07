"""Plans Router — CRUD для тарифных планов"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.plan import GustoPlan, PlanDuration

router = APIRouter(prefix="/api/plans", tags=["Plans"])

class PlanCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    currency: str = "RUB"
    traffic_gb: float = Field(default=100, gt=0)
    duration_days: int = Field(default=30, gt=0)
    duration_type: PlanDuration = PlanDuration.MONTHLY
    device_limit: int = Field(default=3, ge=1)
    ip_limit: int = Field(default=0, ge=0)
    protocol: str = "vless"
    security: str = "reality"
    speed_mbps: int = Field(default=100, gt=0)
    is_premium: bool = False
    is_popular: bool = False
    is_active: bool = True
    sort_order: int = 0
    features: List[str] = []
    referral_discount_percent: float = Field(default=0, ge=0, le=100)

class PlanUpdate(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    traffic_gb: Optional[float] = Field(None, gt=0)
    duration_days: Optional[int] = Field(None, gt=0)
    device_limit: Optional[int] = Field(None, ge=1)
    ip_limit: Optional[int] = Field(None, ge=0)
    is_premium: Optional[bool] = None
    is_popular: Optional[bool] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None
    features: Optional[List[str]] = None
    referral_discount_percent: Optional[float] = Field(None, ge=0, le=100)

class PlanResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: Optional[str]
    price: float
    currency: str
    traffic_gb: float
    duration_days: int
    duration_type: str
    device_limit: int
    ip_limit: int
    protocol: str
    security: str
    speed_mbps: int
    is_premium: bool
    is_popular: bool
    is_active: bool
    sort_order: int
    features: List[str]
    referral_discount_percent: float
    price_per_day: float
    price_per_gb: float

    class Config:
        from_attributes = True

@router.get("/", response_model=List[PlanResponse])
async def list_plans(
    is_active: Optional[bool] = None,
    is_premium: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """Список тарифных планов"""
    query = select(GustoPlan)

    if is_active is not None:
        query = query.where(GustoPlan.is_active == is_active)
    if is_premium is not None:
        query = query.where(GustoPlan.is_premium == is_premium)

    query = query.order_by(GustoPlan.sort_order, GustoPlan.price)

    result = await db.execute(query)
    plans = result.scalars().all()

    return [
        PlanResponse(
            **{c.name: getattr(p, c.name) for c in p.__table__.columns},
            price_per_day=p.price_per_day,
            price_per_gb=p.price_per_gb
        )
        for p in plans
    ]

@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: int, db: AsyncSession = Depends(get_db)):
    """Получить тариф по ID"""
    result = await db.execute(select(GustoPlan).where(GustoPlan.id == plan_id))
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    return PlanResponse(
        **{c.name: getattr(plan, c.name) for c in plan.__table__.columns},
        price_per_day=plan.price_per_day,
        price_per_gb=plan.price_per_gb
    )

@router.post("/", response_model=PlanResponse)
async def create_plan(plan_data: PlanCreate, db: AsyncSession = Depends(get_db)):
    """Создать тариф"""
    plan = GustoPlan(**plan_data.model_dump())
    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    return PlanResponse(
        **{c.name: getattr(plan, c.name) for c in plan.__table__.columns},
        price_per_day=plan.price_per_day,
        price_per_gb=plan.price_per_gb
    )

@router.put("/{plan_id}", response_model=PlanResponse)
async def update_plan(plan_id: int, plan_data: PlanUpdate, db: AsyncSession = Depends(get_db)):
    """Обновить тариф"""
    result = await db.execute(select(GustoPlan).where(GustoPlan.id == plan_id))
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    update_data = plan_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)

    await db.commit()
    await db.refresh(plan)

    return PlanResponse(
        **{c.name: getattr(plan, c.name) for c in plan.__table__.columns},
        price_per_day=plan.price_per_day,
        price_per_gb=plan.price_per_gb
    )

@router.delete("/{plan_id}")
async def delete_plan(plan_id: int, db: AsyncSession = Depends(get_db)):
    """Удалить тариф (soft delete — set is_active=False)"""
    result = await db.execute(select(GustoPlan).where(GustoPlan.id == plan_id))
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan.is_active = False
    await db.commit()

    return {"status": "deleted", "id": plan_id}

@router.post("/seed")
async def seed_default_plans(db: AsyncSession = Depends(get_db)):
    """Создать дефолтные тарифы"""
    defaults = [
        {
            "name": "starter",
            "display_name": "GUSTO Start",
            "description": "Базовый тариф для начинающих",
            "price": 199,
            "traffic_gb": 50,
            "duration_days": 30,
            "device_limit": 2,
            "speed_mbps": 50,
            "sort_order": 1,
            "features": ["VLESS + Reality", "2 устройства", "Базовая поддержка"]
        },
        {
            "name": "pro",
            "display_name": "GUSTO Pro",
            "description": "Оптимальный выбор для большинства пользователей",
            "price": 349,
            "traffic_gb": 100,
            "duration_days": 30,
            "device_limit": 5,
            "speed_mbps": 100,
            "is_popular": True,
            "sort_order": 2,
            "features": ["VLESS + Reality", "5 устройств", "Приоритетная поддержка", "Smart Router"]
        },
        {
            "name": "ultra",
            "display_name": "GUSTO Ultra",
            "description": "Максимум возможностей",
            "price": 599,
            "traffic_gb": 200,
            "duration_days": 30,
            "device_limit": 10,
            "speed_mbps": 200,
            "is_premium": True,
            "sort_order": 3,
            "features": ["VLESS + Reality", "10 устройств", "VIP поддержка", "Smart Router", "Premium серверы"]
        },
        {
            "name": "quarterly",
            "display_name": "GUSTO 3 месяца",
            "description": "Экономия 15%",
            "price": 899,
            "traffic_gb": 300,
            "duration_days": 90,
            "duration_type": PlanDuration.QUARTERLY,
            "device_limit": 5,
            "speed_mbps": 100,
            "sort_order": 4,
            "features": ["VLESS + Reality", "5 устройств", "Экономия 15%", "Smart Router"]
        },
        {
            "name": "annual",
            "display_name": "GUSTO 1 год",
            "description": "Максимальная экономия — 30%",
            "price": 2999,
            "traffic_gb": 1200,
            "duration_days": 365,
            "duration_type": PlanDuration.ANNUAL,
            "device_limit": 10,
            "speed_mbps": 200,
            "is_premium": True,
            "sort_order": 5,
            "features": ["VLESS + Reality", "10 устройств", "Экономия 30%", "VIP поддержка", "Premium серверы"]
        }
    ]

    created = []
    for data in defaults:
        result = await db.execute(select(GustoPlan).where(GustoPlan.name == data["name"]))
        existing = result.scalar_one_or_none()
        if not existing:
            plan = GustoPlan(**data)
            db.add(plan)
            created.append(data["name"])

    await db.commit()
    return {"status": "seeded", "created": created, "total": len(created)}
