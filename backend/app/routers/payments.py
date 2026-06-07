"""
GUSTO Payment Services — интеграция с платежными системами
CryptoBot, YooKassa, FreeKassa
"""
import httpx
import hashlib
import hmac
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

logger = logging.getLogger("gusto.payments")

# ==================== BASE PAYMENT CLASS ====================

class BasePaymentProvider:
    """Базовый класс для платежных провайдеров"""

    def __init__(self, name: str):
        self.name = name

    async def create_payment(self, amount: float, description: str, 
                           order_id: str, **kwargs) -> Optional[Dict]:
        raise NotImplementedError

    async def check_payment(self, payment_id: str) -> Optional[Dict]:
        raise NotImplementedError

    def verify_webhook(self, data: Dict, signature: str) -> bool:
        raise NotImplementedError

# ==================== CRYPTOBOT ====================

class CryptoBotPayment(BasePaymentProvider):
    """
    CryptoBot Payment Provider
    Документация: https://pay.crypt.bot/
    """

    API_URL = "https://pay.crypt.bot/api"

    def __init__(self, api_token: str):
        super().__init__("CryptoBot")
        self.api_token = api_token
        self.headers = {
            "Crypto-Pay-API-Token": api_token,
            "Content-Type": "application/json"
        }
        self.client = httpx.AsyncClient(base_url=self.API_URL, headers=self.headers, timeout=30.0)

    async def create_payment(
        self,
        amount: float,
        description: str,
        order_id: str,
        currency: str = "USDT",
        **kwargs
    ) -> Optional[Dict]:
        """Создать инвойс в CryptoBot"""
        try:
            payload = {
                "asset": currency,
                "amount": str(amount),
                "description": description,
                "payload": json.dumps({"order_id": order_id}),
                "paid_btn_name": "viewItem",
                "paid_btn_url": kwargs.get("success_url", "https://t.me/gustovpn_bot"),
                "allow_comments": False,
                "allow_anonymous": False
            }

            resp = await self.client.post("/createInvoice", json=payload)
            data = resp.json()

            if resp.status_code == 200 and data.get("ok"):
                result = data["result"]
                return {
                    "provider": "cryptobot",
                    "provider_payment_id": str(result["invoice_id"]),
                    "pay_url": result["pay_url"],
                    "amount": float(result["amount"]),
                    "currency": result["asset"],
                    "status": "pending",
                    "expires_at": result.get("expiration_date_time")
                }

            logger.error(f"CryptoBot create error: {data}")
            return None

        except Exception as e:
            logger.error(f"CryptoBot error: {e}")
            return None

    async def check_payment(self, invoice_id: str) -> Optional[Dict]:
        """Проверить статус инвойса"""
        try:
            resp = await self.client.get(f"/getInvoices?invoice_ids={invoice_id}")
            data = resp.json()

            if resp.status_code == 200 and data.get("ok"):
                items = data["result"].get("items", [])
                if items:
                    invoice = items[0]
                    return {
                        "status": "success" if invoice["status"] == "paid" else "pending",
                        "amount": float(invoice["amount"]),
                        "currency": invoice["asset"],
                        "paid_at": invoice.get("paid_at")
                    }
            return None

        except Exception as e:
            logger.error(f"CryptoBot check error: {e}")
            return None

    def verify_webhook(self, data: Dict, signature: str) -> bool:
        """Проверить подпись webhook от CryptoBot"""
        # CryptoBot использует секретный ключ для подписи
        # Реализация зависит от спецификации webhook
        return True  # Заглушка — реализовать по документации

    async def get_balance(self) -> Optional[Dict]:
        """Получить баланс CryptoBot"""
        try:
            resp = await self.client.get("/getBalance")
            data = resp.json()
            if resp.status_code == 200 and data.get("ok"):
                return data["result"]
            return None
        except Exception as e:
            logger.error(f"CryptoBot balance error: {e}")
            return None

    async def close(self):
        await self.client.aclose()

# ==================== YOOKASSA ====================

class YooKassaPayment(BasePaymentProvider):
    """
    YooKassa (ЮKassa) Payment Provider
    Документация: https://yookassa.ru/developers/
    """

    API_URL = "https://api.yookassa.ru/v3"

    def __init__(self, shop_id: str, secret_key: str):
        super().__init__("YooKassa")
        self.shop_id = shop_id
        self.secret_key = secret_key
        self.auth = httpx.BasicAuth(shop_id, secret_key)
        self.headers = {
            "Content-Type": "application/json",
            "Idempotence-Key": ""  # Будет установлено при каждом запросе
        }
        self.client = httpx.AsyncClient(base_url=self.API_URL, auth=self.auth, timeout=30.0)

    def _generate_idempotence_key(self) -> str:
        """Генерировать уникальный ключ идемпотентности"""
        return hashlib.sha256(f"{datetime.utcnow().timestamp()}_{id(self)}".encode()).hexdigest()

    async def create_payment(
        self,
        amount: float,
        description: str,
        order_id: str,
        return_url: str = "https://t.me/gustovpn_bot",
        **kwargs
    ) -> Optional[Dict]:
        """Создать платеж в YooKassa"""
        try:
            self.headers["Idempotence-Key"] = self._generate_idempotence_key()

            payload = {
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": "RUB"
                },
                "capture": True,
                "confirmation": {
                    "type": "redirect",
                    "return_url": return_url
                },
                "description": description,
                "metadata": {
                    "order_id": order_id,
                    "user_id": str(kwargs.get("user_id", ""))
                },
                "receipt": {
                    "customer": {
                        "email": kwargs.get("email", "user@gustovpn.ru")
                    },
                    "items": [{
                        "description": description,
                        "quantity": "1.00",
                        "amount": {
                            "value": f"{amount:.2f}",
                            "currency": "RUB"
                        },
                        "vat_code": "1",  # Без НДС
                        "payment_mode": "full_payment",
                        "payment_subject": "service"
                    }]
                }
            }

            resp = await self.client.post(
                "/payments",
                json=payload,
                headers=self.headers
            )
            data = resp.json()

            if resp.status_code in (200, 201):
                confirmation = data.get("confirmation", {})
                return {
                    "provider": "yookassa",
                    "provider_payment_id": data["id"],
                    "pay_url": confirmation.get("confirmation_url"),
                    "amount": float(data["amount"]["value"]),
                    "currency": data["amount"]["currency"],
                    "status": "pending",
                    "expires_at": None
                }

            logger.error(f"YooKassa create error: {data}")
            return None

        except Exception as e:
            logger.error(f"YooKassa error: {e}")
            return None

    async def check_payment(self, payment_id: str) -> Optional[Dict]:
        """Проверить статус платежа YooKassa"""
        try:
            resp = await self.client.get(f"/payments/{payment_id}")
            data = resp.json()

            if resp.status_code == 200:
                status_map = {
                    "pending": "pending",
                    "waiting_for_capture": "pending",
                    "succeeded": "success",
                    "canceled": "failed",
                    "refunded": "refunded"
                }

                return {
                    "status": status_map.get(data["status"], "pending"),
                    "amount": float(data["amount"]["value"]),
                    "currency": data["amount"]["currency"],
                    "paid_at": data.get("captured_at"),
                    "metadata": data.get("metadata", {})
                }
            return None

        except Exception as e:
            logger.error(f"YooKassa check error: {e}")
            return None

    def verify_webhook(self, data: Dict, signature: str) -> bool:
        """Проверить подпись webhook от YooKassa"""
        # YooKassa использует IP-фильтрацию и basic auth
        # Дополнительная проверка подписи не требуется
        return True

    async def refund_payment(self, payment_id: str, amount: float) -> Optional[Dict]:
        """Возврат платежа"""
        try:
            self.headers["Idempotence-Key"] = self._generate_idempotence_key()

            payload = {
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": "RUB"
                }
            }

            resp = await self.client.post(
                f"/payments/{payment_id}/refunds",
                json=payload,
                headers=self.headers
            )

            if resp.status_code in (200, 201):
                return resp.json()
            return None

        except Exception as e:
            logger.error(f"YooKassa refund error: {e}")
            return None

    async def close(self):
        await self.client.aclose()

# ==================== FREEKASSA ====================

class FreeKassaPayment(BasePaymentProvider):
    """
    FreeKassa Payment Provider
    Документация: https://docs.freekassa.ru/
    """

    API_URL = "https://api.freekassa.ru/v1"
    PAY_URL = "https://pay.freekassa.ru/"

    def __init__(self, shop_id: str, secret_key: str, api_key: str):
        super().__init__("FreeKassa")
        self.shop_id = shop_id
        self.secret_key = secret_key
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json"
        }
        self.client = httpx.AsyncClient(base_url=self.API_URL, timeout=30.0)

    def _generate_sign(self, params: Dict) -> str:
        """Генерировать подпись для FreeKassa"""
        # Формат: MD5(shop_id:amount:secret_key:currency_id)
        sign_string = f"{self.shop_id}:{params['amount']}:{self.secret_key}:{params.get('currency', 'RUB')}"
        return hashlib.md5(sign_string.encode()).hexdigest()

    async def create_payment(
        self,
        amount: float,
        description: str,
        order_id: str,
        currency: str = "RUB",
        **kwargs
    ) -> Optional[Dict]:
        """Создать платеж в FreeKassa"""
        try:
            params = {
                "m": self.shop_id,
                "oa": f"{amount:.2f}",
                "o": order_id,
                "s": self._generate_sign({"amount": f"{amount:.2f}", "currency": currency}),
                "currency": currency,
                "us_user_id": str(kwargs.get("user_id", "")),
                "us_plan_id": str(kwargs.get("plan_id", ""))
            }

            # Формируем URL для оплаты
            query = "&".join([f"{k}={v}" for k, v in params.items()])
            pay_url = f"{self.PAY_URL}?{query}"

            return {
                "provider": "freekassa",
                "provider_payment_id": order_id,
                "pay_url": pay_url,
                "amount": amount,
                "currency": currency,
                "status": "pending",
                "expires_at": None
            }

        except Exception as e:
            logger.error(f"FreeKassa error: {e}")
            return None

    async def check_payment(self, order_id: str) -> Optional[Dict]:
        """Проверить статус платежа через API FreeKassa"""
        try:
            params = {
                "shopId": self.shop_id,
                "nonce": str(int(datetime.utcnow().timestamp())),
                "orderId": order_id
            }

            # Подпись для API запроса
            sign_string = f"{params['shopId']}{params['nonce']}{self.api_key}"
            params["signature"] = hashlib.md5(sign_string.encode()).hexdigest()

            resp = await self.client.post("/orders", json=params)
            data = resp.json()

            if resp.status_code == 200 and data.get("type") == "success":
                order = data.get("order", {})
                return {
                    "status": "success" if order.get("status") == "1" else "pending",
                    "amount": float(order.get("amount", 0)),
                    "currency": order.get("currency", "RUB"),
                    "paid_at": order.get("date")
                }
            return None

        except Exception as e:
            logger.error(f"FreeKassa check error: {e}")
            return None

    def verify_webhook(self, data: Dict) -> bool:
        """Проверить подпись webhook от FreeKassa"""
        # FreeKassa webhook: MD5(shop_id:amount:secret_key:order_id)
        amount = data.get("AMOUNT", "")
        order_id = data.get("MERCHANT_ORDER_ID", "")
        sign = data.get("SIGN", "")

        expected_sign = hashlib.md5(
            f"{self.shop_id}:{amount}:{self.secret_key}:{order_id}".encode()
        ).hexdigest()

        return hmac.compare_digest(sign.lower(), expected_sign.lower())

    async def get_payment_methods(self) -> Optional[Dict]:
        """Получить доступные способы оплаты"""
        try:
            params = {
                "shopId": self.shop_id,
                "nonce": str(int(datetime.utcnow().timestamp()))
            }
            sign_string = f"{params['shopId']}{params['nonce']}{self.api_key}"
            params["signature"] = hashlib.md5(sign_string.encode()).hexdigest()

            resp = await self.client.post("/currencies", json=params)
            if resp.status_code == 200:
                return resp.json()
            return None

        except Exception as e:
            logger.error(f"FreeKassa methods error: {e}")
            return None

    async def close(self):
        await self.client.aclose()

# ==================== PAYMENT MANAGER ====================

class PaymentManager:
    """Менеджер платежей — выбор провайдера и обработка"""

    def __init__(self):
        self.providers: Dict[str, BasePaymentProvider] = {}

    def register_provider(self, provider: BasePaymentProvider):
        """Зарегистрировать платежный провайдер"""
        self.providers[provider.name.lower()] = provider
        logger.info(f"✅ Registered payment provider: {provider.name}")

    async def create_payment(
        self,
        provider_name: str,
        amount: float,
        description: str,
        order_id: str,
        **kwargs
    ) -> Optional[Dict]:
        """Создать платеж через выбранный провайдер"""
        provider = self.providers.get(provider_name.lower())
        if not provider:
            logger.error(f"❌ Provider {provider_name} not found")
            return None

        result = await provider.create_payment(amount, description, order_id, **kwargs)
        if result:
            result["provider_name"] = provider_name
            logger.info(f"✅ Payment created: {provider_name} {amount}₽ order={order_id}")
        return result

    async def check_payment(self, provider_name: str, payment_id: str) -> Optional[Dict]:
        """Проверить статус платежа"""
        provider = self.providers.get(provider_name.lower())
        if not provider:
            return None
        return await provider.check_payment(payment_id)

    def verify_webhook(self, provider_name: str, data: Dict, signature: str = "") -> bool:
        """Проверить webhook"""
        provider = self.providers.get(provider_name.lower())
        if not provider:
            return False
        return provider.verify_webhook(data, signature)

    async def close_all(self):
        """Закрыть все соединения"""
        for provider in self.providers.values():
            if hasattr(provider, 'close'):
                await provider.close()

# ==================== BACKEND ROUTERS (FastAPI) ====================

"""
# Добавить в backend/app/routers/payments.py:

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import GustoPayment, GustoUser, GustoSubscription
from app.services.payments import PaymentManager, CryptoBotPayment, YooKassaPayment, FreeKassaPayment
from app.config import settings

router = APIRouter()

# Инициализация менеджера платежей
payment_manager = PaymentManager()

@router.on_event("startup")
async def init_payment_providers():
    if settings.CRYPTOBOT_TOKEN:
        payment_manager.register_provider(CryptoBotPayment(settings.CRYPTOBOT_TOKEN))
    if settings.YOOKASSA_SHOP_ID and settings.YOOKASSA_SECRET_KEY:
        payment_manager.register_provider(YooKassaPayment(
            settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY
        ))
    if settings.FREEKASSA_ID and settings.FREEKASSA_SECRET:
        payment_manager.register_provider(FreeKassaPayment(
            settings.FREEKASSA_ID, settings.FREEKASSA_SECRET, settings.FREEKASSA_API_KEY
        ))

@router.post("/")
async def create_payment(
    data: dict,
    db: AsyncSession = Depends(get_db)
):
    user_id = data.get("user_id")
    plan_id = data.get("plan_id")
    method = data.get("method", "yookassa")

    # Получить пользователя и тариф
    user = await db.get(GustoUser, user_id)
    plan = await db.get(GustoPlan, plan_id)

    if not user or not plan:
        raise HTTPException(404, "User or plan not found")

    # Создать запись о платеже
    payment = GustoPayment(
        user_id=user_id,
        amount=plan.price,
        currency="RUB",
        method=method
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    # Создать платеж через провайдера
    result = await payment_manager.create_payment(
        provider_name=method,
        amount=float(plan.price),
        description=f"GUSTO VPN — {plan.name}",
        order_id=str(payment.id),
        user_id=user_id,
        plan_id=plan_id,
        email=user.username or f"user{user_id}@gustovpn.ru"
    )

    if not result:
        payment.status = "failed"
        await db.commit()
        raise HTTPException(500, "Failed to create payment")

    # Обновить запись
    payment.provider_payment_id = result["provider_payment_id"]
    payment.provider_data = result
    await db.commit()

    return {
        "payment_id": payment.id,
        "pay_url": result["pay_url"],
        "amount": result["amount"],
        "currency": result["currency"],
        "status": payment.status
    }

@router.get("/{payment_id}")
async def get_payment_status(
    payment_id: int,
    db: AsyncSession = Depends(get_db)
):
    payment = await db.get(GustoPayment, payment_id)
    if not payment:
        raise HTTPException(404, "Payment not found")

    # Проверить статус у провайдера
    if payment.provider_payment_id and payment.status == "pending":
        result = await payment_manager.check_payment(
            payment.method,
            payment.provider_payment_id
        )

        if result and result["status"] == "success":
            payment.status = "success"
            payment.paid_at = datetime.utcnow()

            # Активировать подписку
            # ... (логика активации)

            await db.commit()

    return {
        "id": payment.id,
        "status": payment.status,
        "amount": float(payment.amount),
        "method": payment.method,
        "paid_at": payment.paid_at
    }

# Webhooks

@router.post("/webhook/cryptobot")
async def cryptobot_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()

    # Проверить подпись
    # ...

    # Обработать webhook
    invoice_id = data.get("payload", {}).get("invoice_id")
    status = data.get("payload", {}).get("status")

    if status == "paid":
        # Найти платеж по provider_payment_id
        result = await db.execute(
            select(GustoPayment).where(
                GustoPayment.provider_payment_id == str(invoice_id)
            )
        )
        payment = result.scalar_one_or_none()

        if payment:
            payment.status = "success"
            payment.paid_at = datetime.utcnow()
            await db.commit()

            # Активировать подписку
            # ...

    return {"status": "processed"}

@router.post("/webhook/yookassa")
async def yookassa_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()

    payment_id = data.get("object", {}).get("id")
    status = data.get("object", {}).get("status")

    if status == "succeeded":
        result = await db.execute(
            select(GustoPayment).where(
                GustoPayment.provider_payment_id == payment_id
            )
        )
        payment = result.scalar_one_or_none()

        if payment:
            payment.status = "success"
            payment.paid_at = datetime.utcnow()
            await db.commit()

            # Активировать подписку
            # ...

    return {"status": "processed"}

@router.post("/webhook/freekassa")
async def freekassa_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.form()
    data_dict = dict(data)

    # Проверить подпись
    provider = payment_manager.providers.get("freekassa")
    if provider and not provider.verify_webhook(data_dict):
        raise HTTPException(403, "Invalid signature")

    order_id = data_dict.get("MERCHANT_ORDER_ID")
    status = data_dict.get("STATUS")

    if status == "1":  # Успешный платеж
        result = await db.execute(
            select(GustoPayment).where(
                GustoPayment.provider_payment_id == order_id
            )
        )
        payment = result.scalar_one_or_none()

        if payment:
            payment.status = "success"
            payment.paid_at = datetime.utcnow()
            await db.commit()

            # Активировать подписку
            # ...

    return {"status": "processed"}
"""
