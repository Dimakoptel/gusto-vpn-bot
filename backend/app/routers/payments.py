"""Payments Router v2.0 — Full activation + webhooks + IP whitelist"""
import hashlib
import hmac
import base64
import uuid
import ipaddress
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, Header
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel, Field
import httpx

from app.database import get_db
from app.services.config_service import ConfigService
from app.services.notification_service import NotificationService
from app.services.subscription_service import SubscriptionService
from app.models.payment import GustoPayment, PaymentStatus, PaymentMethod
from app.models.user import GustoUser
from app.models.subscription import GustoSubscription, SubscriptionStatus

logger = logging.getLogger("gusto.payments")
router = APIRouter(prefix="/api/payments", tags=["Payments"])

# ==================== IP WHITELISTS ====================
CRYPTOBOT_IPS = ["185.71.76.0/27", "185.71.77.0/27", "77.75.153.0/25", "77.75.154.128/25", "2a00:bdc0::/32"]
YOOKASSA_IPS = ["185.71.76.0/27", "185.71.77.0/27", "77.75.153.0/25", "77.75.154.128/25", "2a00:bdc0::/32"]

async def verify_webhook_ip(request: Request, allowed_ips: List[str]) -> bool:
    """Проверить IP webhook'а по whitelist"""
    client_ip = request.client.host
    try:
        client_addr = ipaddress.ip_address(client_ip)
        for network in allowed_ips:
            if client_addr in ipaddress.ip_network(network, strict=False):
                return True
    except ValueError:
        pass
    logger.warning(f"⚠️ Webhook from unauthorized IP: {client_ip}")
    return False

# ==================== SCHEMAS ====================
class CreatePaymentRequest(BaseModel):
    user_id: int
    plan_id: int
    provider: str = Field(..., pattern="^(cryptobot|yookassa|freekassa)$")
    amount: float = Field(..., gt=0)
    subscription_id: Optional[int] = None
    currency: str = "RUB"

class PaymentResponse(BaseModel):
    id: int
    status: str
    provider: str
    amount: float
    pay_url: Optional[str] = None
    invoice_id: Optional[str] = None
    expires_at: Optional[str] = None

# ==================== CREATE PAYMENT ====================
@router.post("/", response_model=PaymentResponse)
async def create_payment(
    req: CreatePaymentRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Создать платеж — выбор провайдера, создание подписки PENDING, создание инвойса"""

    # Get user
    result = await db.execute(select(GustoUser).where(GustoUser.id == req.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Create subscription if not exists (for new purchases)
    subscription_id = req.subscription_id
    if not subscription_id:
        sub_service = SubscriptionService(db)
        try:
            sub_data = await sub_service.create_pending(
                user_id=req.user_id,
                plan_id=req.plan_id,
                country_code=user.country_code or "RU"
            )
            subscription_id = sub_data["subscription_id"]
        except Exception as e:
            logger.error(f"❌ Failed to create pending subscription: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create subscription: {str(e)}")

    # Create payment record
    payment = GustoPayment(
        user_id=req.user_id,
        subscription_id=subscription_id,
        plan_id=req.plan_id,
        amount=req.amount,
        currency=req.currency,
        method=PaymentMethod(req.provider),
        status=PaymentStatus.PENDING,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    # Create invoice via provider
    if req.provider == "cryptobot":
        return await _create_cryptobot_invoice(payment, db)
    elif req.provider == "yookassa":
        return await _create_yookassa_invoice(payment, db)
    elif req.provider == "freekassa":
        return await _create_freekassa_invoice(payment, db)
    else:
        raise HTTPException(status_code=400, detail="Unknown provider")

# ==================== CRYPTOBOT ====================
async def _create_cryptobot_invoice(payment: GustoPayment, db: AsyncSession) -> PaymentResponse:
    """Создать инвойс в CryptoBot"""
    service = ConfigService(db)
    config = await service.get_payment_config("cryptobot")
    token = config.get("token")

    if not token:
        raise HTTPException(status_code=400, detail="CryptoBot not configured")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://pay.crypt.bot/api/createInvoice",
            headers={"Crypto-Pay-API-Token": token, "Content-Type": "application/json"},
            json={
                "asset": "USDT",
                "amount": str(payment.amount),
                "description": f"GUSTO VPN — Подписка #{payment.plan_id}",
                "payload": json.dumps({"payment_id": payment.id, "subscription_id": payment.subscription_id}),
                "paid_btn_name": "viewItem",
                "paid_btn_url": "https://t.me/gustovpn_bot",
                "allow_comments": False,
                "allow_anonymous": False
            }
        )

    if resp.status_code != 200:
        payment.status = PaymentStatus.FAILED
        await db.commit()
        raise HTTPException(status_code=500, detail=f"CryptoBot error: {resp.text}")

    data = resp.json()
    if not data.get("ok"):
        payment.status = PaymentStatus.FAILED
        await db.commit()
        raise HTTPException(status_code=500, detail=f"CryptoBot error: {data}")

    result = data["result"]
    payment.provider_payment_id = str(result["invoice_id"])
    payment.provider_data = result
    await db.commit()

    return PaymentResponse(
        id=payment.id,
        status="pending",
        provider="cryptobot",
        amount=payment.amount,
        pay_url=result["pay_url"],
        invoice_id=str(result["invoice_id"]),
        expires_at=result.get("expiration_date_time")
    )

@router.post("/webhook/cryptobot")
async def cryptobot_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Webhook от CryptoBot — проверка IP, активация подписки"""
    # Verify IP (ENABLED!)
    if not await verify_webhook_ip(request, CRYPTOBOT_IPS):
        raise HTTPException(status_code=403, detail="Unauthorized IP")

    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    if data.get("update_type") != "invoice_paid":
        return {"ok": True}

    payload = data.get("payload", {})
    invoice_id = payload.get("invoice_id")

    if not invoice_id:
        return {"ok": False}

    # Find payment by provider_payment_id
    result = await db.execute(
        select(GustoPayment).where(
            GustoPayment.provider_payment_id == str(invoice_id),
            GustoPayment.status == PaymentStatus.PENDING
        )
    )
    payment = result.scalar_one_or_none()

    if not payment:
        logger.warning(f"⚠️ CryptoBot webhook: payment not found for invoice {invoice_id}")
        return {"ok": True}

    # Activate!
    payment.status = PaymentStatus.SUCCESS
    payment.paid_at = datetime.utcnow()
    payment.provider_data = {**payment.provider_data, "webhook_data": data}
    await db.commit()

    # Activate subscription (CRITICAL!)
    try:
        sub_service = SubscriptionService(db)
        activation = await sub_service.activate_after_payment(payment)
        logger.info(f"✅ Subscription activated via CryptoBot: {activation}")
    except Exception as e:
        logger.error(f"❌ Failed to activate subscription after CryptoBot payment: {e}")
        # Payment is marked success but subscription failed — needs manual intervention
        # Could add to retry queue

    return {"ok": True}

# ==================== YOOKASSA ====================
async def _create_yookassa_invoice(payment: GustoPayment, db: AsyncSession) -> PaymentResponse:
    """Создать платеж в YooKassa"""
    service = ConfigService(db)
    config = await service.get_payment_config("yookassa")
    shop_id = config.get("shop_id")
    secret_key = config.get("secret_key")

    if not shop_id or not secret_key:
        raise HTTPException(status_code=400, detail="YooKassa not configured")

    auth = base64.b64encode(f"{shop_id}:{secret_key}".encode()).decode()
    idempotence_key = str(uuid.uuid4())

    request_body = {
        "amount": {"value": f"{payment.amount:.2f}", "currency": payment.currency or "RUB"},
        "capture": True,
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/gustovpn_bot"
        },
        "description": f"GUSTO VPN — Подписка #{payment.plan_id}",
        "metadata": {
            "payment_id": str(payment.id),
            "subscription_id": str(payment.subscription_id),
            "user_id": str(payment.user_id)
        },
        "receipt": {
            "customer": {"email": "user@gustovpn.ru"},
            "items": [{
                "description": "VPN подписка",
                "quantity": "1.00",
                "amount": {"value": f"{payment.amount:.2f}", "currency": payment.currency or "RUB"},
                "vat_code": "1",
                "payment_mode": "full_payment",
                "payment_subject": "service"
            }]
        }
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.yookassa.ru/v3/payments",
            headers={
                "Authorization": f"Basic {auth}",
                "Idempotence-Key": idempotence_key,
                "Content-Type": "application/json"
            },
            json=request_body
        )

    if resp.status_code not in (200, 201):
        payment.status = PaymentStatus.FAILED
        await db.commit()
        raise HTTPException(status_code=500, detail=f"YooKassa error: {resp.text}")

    data = resp.json()
    payment.provider_payment_id = data["id"]
    payment.provider_data = data
    await db.commit()

    return PaymentResponse(
        id=payment.id,
        status="pending",
        provider="yookassa",
        amount=payment.amount,
        pay_url=data["confirmation"]["confirmation_url"],
        invoice_id=data["id"],
        expires_at=None
    )

@router.post("/webhook/yookassa")
async def yookassa_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Webhook от YooKassa — активация подписки"""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event = data.get("event", "")
    obj = data.get("object", {})

    if event not in ("payment.succeeded", "payment.captured"):
        return {"ok": True}

    payment_id = obj.get("metadata", {}).get("payment_id")
    if not payment_id:
        return {"ok": False}

    result = await db.execute(
        select(GustoPayment).where(
            GustoPayment.id == int(payment_id),
            GustoPayment.status == PaymentStatus.PENDING
        )
    )
    payment = result.scalar_one_or_none()

    if not payment:
        logger.warning(f"⚠️ YooKassa webhook: payment {payment_id} not found or not pending")
        return {"ok": True}

    # Activate!
    payment.status = PaymentStatus.SUCCESS
    payment.paid_at = datetime.utcnow()
    payment.provider_data = {**payment.provider_data, "webhook_data": data}
    await db.commit()

    # Activate subscription (CRITICAL!)
    try:
        sub_service = SubscriptionService(db)
        activation = await sub_service.activate_after_payment(payment)
        logger.info(f"✅ Subscription activated via YooKassa: {activation}")
    except Exception as e:
        logger.error(f"❌ Failed to activate subscription after YooKassa payment: {e}")

    return {"ok": True}

# ==================== FREEKASSA ====================
async def _create_freekassa_invoice(payment: GustoPayment, db: AsyncSession) -> PaymentResponse:
    """Создать платеж в FreeKassa"""
    service = ConfigService(db)
    config = await service.get_payment_config("freekassa")
    fk_id = config.get("id")
    fk_secret = config.get("secret")

    if not fk_id or not fk_secret:
        raise HTTPException(status_code=400, detail="FreeKassa not configured")

    sign = hashlib.md5(
        f"{fk_id}:{payment.amount:.2f}:{fk_secret}:{payment.id}".encode()
    ).hexdigest()

    pay_url = (
        f"https://pay.freekassa.ru/?"
        f"m={fk_id}&"
        f"oa={payment.amount:.2f}&"
        f"o={payment.id}&"
        f"s={sign}&"
        f"us_user_id={payment.user_id}&"
        f"us_plan_id={payment.plan_id}&"
        f"us_subscription_id={payment.subscription_id}"
    )

    payment.provider_payment_id = str(payment.id)
    await db.commit()

    return PaymentResponse(
        id=payment.id,
        status="pending",
        provider="freekassa",
        amount=payment.amount,
        pay_url=pay_url,
        invoice_id=str(payment.id),
        expires_at=(datetime.utcnow() + timedelta(hours=1)).isoformat()
    )

@router.post("/webhook/freekassa")
async def freekassa_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Webhook от FreeKassa — проверка подписи, активация подписки"""
    try:
        data = await request.form()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid form data")

    data_dict = dict(data)

    service = ConfigService(db)
    config = await service.get_payment_config("freekassa")
    fk_id = config.get("id")
    fk_secret = config.get("secret")

    # Verify signature
    amount = data_dict.get("AMOUNT", "")
    order_id = data_dict.get("MERCHANT_ORDER_ID", "")
    sign = data_dict.get("SIGN", "")

    expected_sign = hashlib.md5(
        f"{fk_id}:{amount}:{fk_secret}:{order_id}".encode()
    ).hexdigest()

    if not hmac.compare_digest(sign.lower(), expected_sign.lower()):
        logger.warning(f"⚠️ FreeKassa invalid signature for order {order_id}")
        raise HTTPException(status_code=403, detail="Invalid signature")

    status = data_dict.get("STATUS", "")
    if status != "1":  # Not success
        return PlainTextResponse("YES")

    # Find payment
    result = await db.execute(
        select(GustoPayment).where(
            GustoPayment.id == int(order_id),
            GustoPayment.status == PaymentStatus.PENDING
        )
    )
    payment = result.scalar_one_or_none()

    if not payment:
        logger.warning(f"⚠️ FreeKassa webhook: payment {order_id} not found")
        return PlainTextResponse("YES")

    # Activate!
    payment.status = PaymentStatus.SUCCESS
    payment.paid_at = datetime.utcnow()
    payment.provider_data = {**payment.provider_data, "webhook_data": data_dict}
    await db.commit()

    # Activate subscription (CRITICAL!)
    try:
        sub_service = SubscriptionService(db)
        activation = await sub_service.activate_after_payment(payment)
        logger.info(f"✅ Subscription activated via FreeKassa: {activation}")
    except Exception as e:
        logger.error(f"❌ Failed to activate subscription after FreeKassa payment: {e}")

    return PlainTextResponse("YES")

# ==================== STATUS & HISTORY ====================
@router.get("/{payment_id}")
async def get_payment_status(
    payment_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Проверить статус платежа"""
    result = await db.execute(select(GustoPayment).where(GustoPayment.id == payment_id))
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return {
        "id": payment.id,
        "status": payment.status.value,
        "provider": payment.method.value,
        "amount": float(payment.amount),
        "currency": payment.currency,
        "created_at": payment.created_at.isoformat() if payment.created_at else None,
        "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
        "is_expired": False  # Add logic if needed
    }

@router.get("/history/{user_id}")
async def get_user_payments(
    user_id: int,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """История платежей пользователя"""
    result = await db.execute(
        select(GustoPayment)
        .where(GustoPayment.user_id == user_id)
        .order_by(GustoPayment.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    payments = result.scalars().all()

    return [
        {
            "id": p.id,
            "amount": float(p.amount),
            "provider": p.method.value,
            "status": p.status.value,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "paid_at": p.paid_at.isoformat() if p.paid_at else None,
        }
        for p in payments
    ]

@router.post("/{payment_id}/refund")
async def refund_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Возврат платежа (только YooKassa)"""
    result = await db.execute(select(GustoPayment).where(GustoPayment.id == payment_id))
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if payment.method != PaymentMethod.YOOKASSA:
        raise HTTPException(status_code=400, detail="Refund only supported for YooKassa")

    service = ConfigService(db)
    config = await service.get_payment_config("yookassa")
    shop_id = config.get("shop_id")
    secret_key = config.get("secret_key")
    auth = base64.b64encode(f"{shop_id}:{secret_key}".encode()).decode()

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.yookassa.ru/v3/payments/{payment.provider_payment_id}/refunds",
            headers={
                "Authorization": f"Basic {auth}",
                "Idempotence-Key": str(uuid.uuid4()),
                "Content-Type": "application/json"
            },
            json={"amount": {"value": f"{float(payment.amount):.2f}", "currency": payment.currency}}
        )

    if resp.status_code in (200, 201):
        payment.status = PaymentStatus.REFUNDED
        await db.commit()
        return {"status": "refunded"}
    else:
        raise HTTPException(status_code=500, detail=f"Refund failed: {resp.text}")
