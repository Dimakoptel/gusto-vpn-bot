from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timedelta

from app.database import get_db
from app.models import GustoSubscription, GustoUser, GustoServer, GustoPlan
from app.services import GustoX3UIClient, X3UIPanel, GustoSmartRouter

router = APIRouter()


@router.post("/")
async def create_subscription(
    data: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    user_id = data.get("user_id")
    plan_id = data.get("plan_id")
    country = data.get("country_code", "RU")

    user = await db.get(GustoUser, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    plan = await db.get(GustoPlan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")

    servers_result = await db.execute(
        select(GustoServer).where(
            and_(GustoServer.is_active == True, GustoServer.is_online == True)
        )
    )
    servers = servers_result.scalars().all()

    if not servers:
        raise HTTPException(503, "No servers available")

    router = GustoSmartRouter()
    best = await router.find_best(country, servers)

    if not best:
        raise HTTPException(503, "Could not find suitable server")

    server = best.server
    x3ui = GustoX3UIClient(X3UIPanel(
        host=server.host, port=server.port,
        username=server.panel_username, password=server.panel_password,
        name=server.name
    ))

    email = f"user_{user.id}_{int(datetime.utcnow().timestamp())}"
    client = await x3ui.add_client(
        inbound_id=server.vless_inbound_id or 1,
        email=email,
        total_gb=float(plan.traffic_gb),
        expiry_days=plan.duration_days,
        tg_id=user.telegram_id
    )
    await x3ui.close()

    if not client:
        raise HTTPException(500, "Failed to create client in 3x-ui")

    subscription = GustoSubscription(
        user_id=user.id,
        plan_id=plan.id,
        server_id=server.id,
        email=email,
        uuid=client["uuid"],
        inbound_id=server.vless_inbound_id,
        total_gb=plan.traffic_gb,
        expires_at=datetime.utcnow() + timedelta(days=plan.duration_days),
        config_link=client["config"]["link"],
        config_json=client["config"]
    )

    db.add(subscription)
    server.total_users += 1
    await db.commit()
    await db.refresh(subscription)

    return subscription


@router.get("/")
async def list_subscriptions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GustoSubscription))
    return result.scalars().all()
