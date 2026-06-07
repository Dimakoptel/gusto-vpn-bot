"""
Payments Router v2
Читает конфигурацию платежных систем из SystemSettings (админ-панель)
"""
import hashlib
import hmac
import base64
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import httpx

from backend.app.database import get_db
from backend.app.services.config_service import ConfigService
from backend.app.services.notification_service import NotificationService
from backend.app.dependencies import get_current_admin
from backend.app.models.user import User
from backend.app.models.subscription import Subscription, SubscriptionStatus
from backend.app.models.payment import Payment, PaymentStatus, PaymentProvider
from backend.app.services.x3ui_client import X3UIClient

router = APIRouter(prefix="/payments", tags=["Payments"])

# === Schemas ===
class CreatePaymentRequest(BaseModel):
    user_id: int
    plan_id: int
    provider: str = Field(..., regex="^(cryptobot|yookassa|freekassa)$")
    amount: float = Field(..., gt=0)
    referral_discount: Optional[float] = 0

class PaymentResponse(BaseModel):
    id: int
    status: str
    provider: str
    amount: float
    pay_url: Optional[str] = None
    invoice_id: Optional[str] = None
    expires_at: Optional[str] = None

# === Helpers ===
def get_config_service(db: Session) -> ConfigService:
    return ConfigService(db)

# === CryptoBot ===

@router.post("/cryptobot/create", response_model=PaymentResponse)
async def create_cryptobot_payment(
    req: CreatePaymentRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Создать инвойс через CryptoBot (настройки из админ-панели)"""
    config = get_config_service(db).get_payment_config("cryptobot")
    if not config.get("enabled") or not config.get("token"):
        raise HTTPException(status_code=400, detail="CryptoBot отключен или не настроен")

    # Создаем запись в БД
    payment = Payment(
        user_id=req.user_id,
        plan_id=req.plan_id,
        provider=PaymentProvider.CRYPTOBOT,
        amount=req.amount,
        status=PaymentStatus.PENDING,
        expires_at=datetime.utcnow() + timedelta(minutes=30)
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    # Создаем инвойс в CryptoBot
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://pay.crypt.bot/api/createInvoice",
            headers={"Crypto-Pay-API-Token": config["token"]},
            json={
                "asset": "USDT",
                "amount": req.amount,
                "description": f"GUSTO VPN - Подписка #{req.plan_id}",
                "payload": str(payment.id),
                "paid_btn_name": "viewItem",
                "paid_btn_url": f"https://t.me/gusto_vpn_bot",
            }
        )

        if resp.status_code != 200:
            payment.status = PaymentStatus.FAILED
            db.commit()
            raise HTTPException(status_code=500, detail=f"CryptoBot error: {resp.text}")

        data = resp.json()["result"]
        payment.external_id = data["invoice_id"]
        db.commit()

        return PaymentResponse(
            id=payment.id,
            status="pending",
            provider="cryptobot",
            amount=req.amount,
            pay_url=data["pay_url"],
            invoice_id=data["invoice_id"],
            expires_at=payment.expires_at.isoformat()
        )

@router.post("/webhook/cryptobot")
async def cryptobot_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Webhook от CryptoBot"""
    data = await request.json()

    if data.get("update_type") != "invoice_paid":
        return {"ok": True}

    payload = data.get("payload", {}).get("payload")
    payment_id = int(payload) if payload else None

    if not payment_id:
        return {"ok": False}

    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment or payment.status != PaymentStatus.PENDING:
        return {"ok": True}

    # Активируем подписку
    payment.status = PaymentStatus.COMPLETED
    payment.completed_at = datetime.utcnow()
    db.commit()

    # Активируем подписку
    await _activate_subscription(payment, db)

    # Уведомления
    notify = NotificationService(db)
    await notify.payment_success(payment.user_id, payment.amount, payment.provider)

    return {"ok": True}

# === YooKassa ===

@router.post("/yookassa/create", response_model=PaymentResponse)
async def create_yookassa_payment(
    req: CreatePaymentRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Создать платеж через YooKassa (настройки из админ-панели)"""
    config = get_config_service(db).get_payment_config("yookassa")
    if not config.get("enabled") or not config.get("shop_id") or not config.get("secret_key"):
        raise HTTPException(status_code=400, detail="YooKassa отключен или не настроен")

    payment = Payment(
        user_id=req.user_id,
        plan_id=req.plan_id,
        provider=PaymentProvider.YOOKASSA,
        amount=req.amount,
        status=PaymentStatus.PENDING,
        expires_at=datetime.utcnow() + timedelta(minutes=30)
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    idempotence_key = str(uuid.uuid4())
    auth = base64.b64encode(f"{config['shop_id']}:{config['secret_key']}".encode()).decode()

    request_body = {
        "amount": {"value": f"{req.amount:.2f}", "currency": "RUB"},
        "capture": True,
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/gusto_vpn_bot"
        },
        "description": f"GUSTO VPN - Подписка #{req.plan_id}",
        "metadata": {"payment_id": str(payment.id)}
    }

    # Фискальный чек (54-ФЗ)
    if config.get("fiscal_enabled"):
        request_body["receipt"] = {
            "customer": {"email": "user@gusto.vpn"},
            "items": [{
                "description": "VPN подписка",
                "quantity": "1.00",
                "amount": {"value": f"{req.amount:.2f}", "currency": "RUB"},
                "vat_code": 1,
                "payment_subject": "service",
                "payment_mode": "full_payment"
            }]
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
            db.commit()
            raise HTTPException(status_code=500, detail=f"YooKassa error: {resp.text}")

        data = resp.json()
        payment.external_id = data["id"]
        db.commit()

        return PaymentResponse(
            id=payment.id,
            status="pending",
            provider="yookassa",
            amount=req.amount,
            pay_url=data["confirmation"]["confirmation_url"],
            invoice_id=data["id"],
            expires_at=payment.expires_at.isoformat()
        )

@router.post("/webhook/yookassa")
async def yookassa_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Webhook от YooKassa"""
    data = await request.json()

    if data.get("event") != "payment.succeeded":
        return {"ok": True}

    payment_id = int(data["object"]["metadata"].get("payment_id", 0))
    payment = db.query(Payment).filter(Payment.id == payment_id).first()

    if not payment or payment.status != PaymentStatus.PENDING:
        return {"ok": True}

    payment.status = PaymentStatus.COMPLETED
    payment.completed_at = datetime.utcnow()
    db.commit()

    await _activate_subscription(payment, db)

    notify = NotificationService(db)
    await notify.payment_success(payment.user_id, payment.amount, payment.provider)

    return {"ok": True}

# === FreeKassa ===

@router.post("/freekassa/create", response_model=PaymentResponse)
async def create_freekassa_payment(
    req: CreatePaymentRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Создать платеж через FreeKassa (настройки из админ-панели)"""
    config = get_config_service(db).get_payment_config("freekassa")
    if not config.get("enabled") or not config.get("id") or not config.get("secret"):
        raise HTTPException(status_code=400, detail="FreeKassa отключен или не настроен")

    payment = Payment(
        user_id=req.user_id,
        plan_id=req.plan_id,
        provider=PaymentProvider.FREEKASSA,
        amount=req.amount,
        status=PaymentStatus.PENDING,
        expires_at=datetime.utcnow() + timedelta(minutes=60)
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    # Подпись FreeKassa
    sign = hashlib.md5(
        f"{config['id']}:{req.amount}:{config['secret']}:{payment.id}".encode()
    ).hexdigest()

    pay_url = (
        f"https://pay.freekassa.ru/?"
        f"m={config['id']}&"
        f"oa={req.amount}&"
        f"o={payment.id}&"
        f"s={sign}&"
        f"us_user_id={req.user_id}&"
        f"us_plan_id={req.plan_id}"
    )

    return PaymentResponse(
        id=payment.id,
        status="pending",
        provider="freekassa",
        amount=req.amount,
        pay_url=pay_url,
        invoice_id=str(payment.id),
        expires_at=payment.expires_at.isoformat()
    )

@router.post("/webhook/freekassa")
async def freekassa_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Webhook от FreeKassa"""
    data = await request.form()
    config = get_config_service(db).get_payment_config("freekassa")

    payment_id = int(data.get("MERCHANT_ORDER_ID", 0))
    amount = float(data.get("AMOUNT", 0))
    sign = data.get("SIGN", "")

    # Проверка подписи
    expected_sign = hashlib.md5(
        f"{config['id']}:{amount}:{config['secret']}:{payment_id}".encode()
    ).hexdigest()

    if sign != expected_sign:
        raise HTTPException(status_code=400, detail="Invalid signature")

    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment or payment.status != PaymentStatus.PENDING:
        return "YES"

    payment.status = PaymentStatus.COMPLETED
    payment.completed_at = datetime.utcnow()
    db.commit()

    await _activate_subscription(payment, db)

    notify = NotificationService(db)
    await notify.payment_success(payment.user_id, payment.amount, payment.provider)

    return "YES"

# === Common ===

async def _activate_subscription(payment: Payment, db: Session):
    """Активировать подписку после оплаты"""
    from backend.app.services.subscription_service import SubscriptionService

    service = SubscriptionService(db)
    await service.activate_after_payment(payment)

@router.get("/status/{payment_id}")
async def check_payment_status(
    payment_id: int,
    db: Session = Depends(get_db)
):
    """Проверить статус платежа"""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return {
        "id": payment.id,
        "status": payment.status.value,
        "provider": payment.provider.value,
        "amount": payment.amount,
        "created_at": payment.created_at.isoformat() if payment.created_at else None,
        "completed_at": payment.completed_at.isoformat() if payment.completed_at else None,
        "is_expired": payment.expires_at < datetime.utcnow() if payment.expires_at else False
    }

@router.get("/history/{user_id}")
async def get_user_payments(
    user_id: int,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """История платежей пользователя"""
    payments = db.query(Payment).filter(
        Payment.user_id == user_id
    ).order_by(Payment.created_at.desc()).offset(offset).limit(limit).all()

    return [
        {
            "id": p.id,
            "amount": p.amount,
            "provider": p.provider.value,
            "status": p.status.value,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "completed_at": p.completed_at.isoformat() if p.completed_at else None,
        }
        for p in payments
    ]

@router.post("/refund/{payment_id}")
async def refund_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Возврат платежа (только YooKassa)"""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if payment.provider != PaymentProvider.YOOKASSA:
        raise HTTPException(status_code=400, detail="Refund only supported for YooKassa")

    config = get_config_service(db).get_payment_config("yookassa")
    auth = base64.b64encode(f"{config['shop_id']}:{config['secret_key']}".encode()).decode()

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.yookassa.ru/v3/payments/{payment.external_id}/refunds",
            headers={
                "Authorization": f"Basic {auth}",
                "Idempotence-Key": str(uuid.uuid4()),
                "Content-Type": "application/json"
            },
            json={
                "amount": {"value": f"{payment.amount:.2f}", "currency": "RUB"}
            }
        )

        if resp.status_code in (200, 201):
            payment.status = PaymentStatus.REFUNDED
            db.commit()
            return {"status": "refunded"}
        else:
            raise HTTPException(status_code=500, detail=f"Refund failed: {resp.text}")
