"""
GUSTO Subscriptions Router — обновленный с реальными платежами
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from datetime import datetime, timedelta

from app.database import get_db
from app.models import GustoSubscription, GustoUser, GustoServer, GustoPlan, GustoPayment
from app.services.x3ui_client import GustoX3UIClient, X3UIPanel
from app.services.subscription_service import SubscriptionService
from app.services.config_service import ConfigService

router = APIRouter(prefix="/api/subscriptions", tags=["Subscriptions"])

@router.post("/pending")
async def create_pending_subscription(
    data: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    Создать подписку в статусе PENDING (до оплаты)
    Вызывается из бота при выборе тарифа
    """
    user_id = data.get("user_id")
    plan_id = data.get("plan_id")
    country = data.get("country_code", "RU")

    service = SubscriptionService(db)
    try:
        result = await service.create_pending(
            user_id=user_id,
            plan_id=plan_id,
            country_code=country
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to create subscription: {str(e)}")

@router.post("/")
async def create_subscription(
    data: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Создать подписку + платеж (полный flow)
    1. Проверить пользователя и тариф
    2. Выбрать лучший сервер (Smart Router)
    3. Создать клиента в 3x-ui
    4. Создать платеж
    5. Вернуть ссылку на оплату
    """
    user_id = data.get("user_id")
    plan_id = data.get("plan_id")
    country = data.get("country_code", "RU")
    payment_method = data.get("payment_method", "yookassa")

    # 1. Получить пользователя
    user = await db.get(GustoUser, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    # 2. Получить тариф
    plan = await db.get(GustoPlan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")

    if not plan.is_active:
        raise HTTPException(400, "Plan is not active")

    # 3. Получить активные серверы
    servers_result = await db.execute(
        select(GustoServer).where(
            and_(GustoServer.is_active == True, GustoServer.is_online == True)
        )
    )
    servers = servers_result.scalars().all()

    if not servers:
        raise HTTPException(503, "No servers available")

    # 4. Выбрать лучший сервер (Smart Router via SubscriptionService)
    service = SubscriptionService(db)
    server = await service._select_server(country, plan.is_premium)

    if not server:
        raise HTTPException(503, "Could not find suitable server")

    # 5. Подключиться к 3x-ui панели
    x3ui = GustoX3UIClient(X3UIPanel(
        host=server.host,
        port=server.port,
        api_token=server.panel_api_token,
        name=server.name
    ))

    # 6. Создать email для клиента
    email = f"user_{user.id}_{int(datetime.utcnow().timestamp())}"

    # 7. Создать клиента в 3x-ui
    client = await x3ui.create_client(
        inbound_ids=[server.vless_inbound_id or 1],
        email=email,
        total_gb=float(plan.traffic_gb),
        expiry_days=plan.duration_days,
        tg_id=user.telegram_id,
        ip_limit=plan.device_limit or 3
    )

    await x3ui.close()

    if not client:
        raise HTTPException(500, "Failed to create client in 3x-ui")

    # 8. Создать запись о подписке (PENDING — пока не оплачено)
    subscription = GustoSubscription(
        user_id=user.id,
        plan_id=plan.id,
        server_id=server.id,
        email=email,
        uuid=client["uuid"],
        inbound_id=server.vless_inbound_id,
        total_gb=plan.traffic_gb,
        expires_at=datetime.utcnow() + timedelta(days=plan.duration_days),
        status="pending",
        config_link=client.get("config", {}).get("link", ""),
        config_json=client.get("config", {})
    )
    db.add(subscription)
    await db.flush()

    # 9. Создать платеж
    payment = GustoPayment(
        user_id=user.id,
        subscription_id=subscription.id,
        amount=plan.price,
        currency="RUB",
        method=payment_method,
        status="pending"
    )
    db.add(payment)
    await db.flush()

    # 10. Создать платеж через провайдера (используем payments router)
    # NOTE: В реальном flow бот должен вызвать /api/payments/ для создания инвойса
    # Здесь возвращаем subscription_id и payment_id для дальнейшей обработки

    await db.commit()

    return {
        "subscription_id": subscription.id,
        "payment_id": payment.id,
        "amount": float(plan.price),
        "currency": "RUB",
        "status": "pending",
        "server": {
            "name": server.name,
            "location": server.location,
            "country_code": server.country_code
        },
        "plan": {
            "name": plan.name,
            "duration_days": plan.duration_days,
            "traffic_gb": plan.traffic_gb
        }
    }

@router.post("/{subscription_id}/activate")
async def activate_subscription(
    subscription_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Активировать подписку после успешной оплаты
    (вызывается из webhook handler)
    """
    subscription = await db.get(GustoSubscription, subscription_id)
    if not subscription:
        raise HTTPException(404, "Subscription not found")

    if subscription.status != "pending":
        raise HTTPException(400, "Subscription is not pending")

    # Активировать подписку
    subscription.status = "active"
    subscription.started_at = datetime.utcnow()

    # Обновить счетчик пользователей на сервере
    server = await db.get(GustoServer, subscription.server_id)
    if server:
        server.total_users += 1

    await db.commit()

    return {
        "subscription_id": subscription.id,
        "status": "active",
        "email": subscription.email,
        "config_link": subscription.config_link
    }

@router.get("/")
async def list_subscriptions(
    user_id: int = None,
    status: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Список подписок (с фильтрами)"""
    query = select(GustoSubscription)

    if user_id:
        query = query.where(GustoSubscription.user_id == user_id)
    if status:
        query = query.where(GustoSubscription.status == status)

    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{subscription_id}")
async def get_subscription(
    subscription_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получить подписку по ID"""
    subscription = await db.get(GustoSubscription, subscription_id)
    if not subscription:
        raise HTTPException(404, "Subscription not found")
    return subscription

@router.post("/{subscription_id}/renew")
async def renew_subscription(
    subscription_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Продлить подписку"""
    service = SubscriptionService(db)
    try:
        plan_id = data.get("plan_id")
        # Найти платеж для продления (mock — в реальности нужен новый платеж)
        payment = GustoPayment(
            user_id=1,  # placeholder
            subscription_id=subscription_id,
            amount=0,
            currency="RUB",
            method="yookassa",
            status=PaymentStatus.SUCCESS
        )
        result = await service.renew_subscription(subscription_id, plan_id, payment)
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to renew: {str(e)}")

@router.post("/{subscription_id}/cancel")
async def cancel_subscription(
    subscription_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Отменить подписку (отключить клиента)"""
    subscription = await db.get(GustoSubscription, subscription_id)
    if not subscription:
        raise HTTPException(404, "Subscription not found")

    # Получить сервер
    server = await db.get(GustoServer, subscription.server_id)
    if server:
        x3ui = GustoX3UIClient(X3UIPanel(
            host=server.host,
            port=server.port,
            api_token=server.panel_api_token,
            name=server.name
        ))

        # Отключить клиента (disable)
        await x3ui.update_client(
            subscription.email,
            {"enable": False}
        )

        await x3ui.close()

    subscription.status = "suspended"
    await db.commit()

    return {"subscription_id": subscription.id, "status": "suspended"}

@router.post("/{subscription_id}/delete")
async def delete_subscription(
    subscription_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Удалить подписку (полностью удалить клиента из 3x-ui)"""
    subscription = await db.get(GustoSubscription, subscription_id)
    if not subscription:
        raise HTTPException(404, "Subscription not found")

    # Получить сервер
    server = await db.get(GustoServer, subscription.server_id)
    if server:
        x3ui = GustoX3UIClient(X3UIPanel(
            host=server.host,
            port=server.port,
            api_token=server.panel_api_token,
            name=server.name
        ))

        # Удалить клиента
        await x3ui.delete_client(subscription.email)

        await x3ui.close()

        # Обновить счетчик
        server.total_users = max(0, server.total_users - 1)

    subscription.status = "expired"
    await db.commit()

    return {"subscription_id": subscription.id, "status": "deleted"}
