"""
Settings Router
CRUD для SystemSettings + endpoints для админ-панели
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.settings import SystemSettings
from app.services.config_service import ConfigService
from app.dependencies import get_current_admin

router = APIRouter(prefix="/settings", tags=["Settings"])

# === Pydantic Schemas ===

class BotSettingsSchema(BaseModel):
    bot_token: Optional[str] = None
    admin_ids: Optional[List[int]] = None
    support_username: Optional[str] = None
    welcome_message: Optional[str] = None

class PaymentSettingsSchema(BaseModel):
    cryptobot_token: Optional[str] = None
    cryptobot_enabled: Optional[bool] = None
    yookassa_shop_id: Optional[str] = None
    yookassa_secret_key: Optional[str] = None
    yookassa_enabled: Optional[bool] = None
    yookassa_fiscal_enabled: Optional[bool] = None
    freekassa_id: Optional[str] = None
    freekassa_secret: Optional[str] = None
    freekassa_api_key: Optional[str] = None
    freekassa_enabled: Optional[bool] = None

class ReferralSettingsSchema(BaseModel):
    referral_enabled: Optional[bool] = None
    referral_level1_percent: Optional[float] = Field(None, ge=0, le=100)
    referral_level2_percent: Optional[float] = Field(None, ge=0, le=100)
    referral_level3_percent: Optional[float] = Field(None, ge=0, le=100)
    referral_min_payout: Optional[float] = Field(None, ge=0)

class AntifraudSettingsSchema(BaseModel):
    antifraud_enabled: Optional[bool] = None
    antifraud_max_ips: Optional[int] = Field(None, ge=1, le=20)
    antifraud_max_countries: Optional[int] = Field(None, ge=1, le=10)
    antifraud_ban_hours: Optional[int] = Field(None, ge=1, le=720)

class NotificationSettingsSchema(BaseModel):
    notify_expiry_3days: Optional[bool] = None
    notify_expiry_1day: Optional[bool] = None
    notify_expiry_today: Optional[bool] = None
    notify_low_traffic_gb: Optional[float] = Field(None, ge=0.1, le=1000)
    notify_channel_id: Optional[str] = None

class SystemSettingsSchema(BaseModel):
    app_name: Optional[str] = None
    app_logo_url: Optional[str] = None
    maintenance_mode: Optional[bool] = None

class FullSettingsUpdateSchema(BaseModel):
    bot: Optional[BotSettingsSchema] = None
    payments: Optional[PaymentSettingsSchema] = None
    referral: Optional[ReferralSettingsSchema] = None
    antifraud: Optional[AntifraudSettingsSchema] = None
    notifications: Optional[NotificationSettingsSchema] = None
    system: Optional[SystemSettingsSchema] = None

class SettingsResponse(BaseModel):
    id: int
    bot_token: Optional[str]
    admin_ids: List[int]
    support_username: Optional[str]
    welcome_message: Optional[str]
    cryptobot_enabled: bool
    yookassa_enabled: bool
    freekassa_enabled: bool
    referral_enabled: bool
    referral_level1_percent: float
    referral_level2_percent: float
    referral_level3_percent: float
    referral_min_payout: float
    antifraud_enabled: bool
    antifraud_max_ips: int
    antifraud_max_countries: int
    antifraud_ban_hours: int
    notify_expiry_3days: bool
    notify_expiry_1day: bool
    notify_expiry_today: bool
    notify_low_traffic_gb: float
    notify_channel_id: Optional[str]
    app_name: str
    app_logo_url: Optional[str]
    maintenance_mode: bool
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True

# === Endpoints ===

@router.get("/", response_model=SettingsResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Получить все настройки системы"""
    service = ConfigService(db)
    settings = await service.get_settings()
    return settings

@router.put("/", response_model=SettingsResponse)
async def update_settings(
    data: FullSettingsUpdateSchema,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Обновить настройки (любую группу или все сразу)"""
    service = ConfigService(db)

    update_data = {}
    if data.bot:
        update_data.update(data.bot.model_dump(exclude_unset=True))
    if data.payments:
        update_data.update(data.payments.model_dump(exclude_unset=True))
    if data.referral:
        update_data.update(data.referral.model_dump(exclude_unset=True))
    if data.antifraud:
        update_data.update(data.antifraud.model_dump(exclude_unset=True))
    if data.notifications:
        update_data.update(data.notifications.model_dump(exclude_unset=True))
    if data.system:
        update_data.update(data.system.model_dump(exclude_unset=True))

    settings = await service.update_settings(update_data, admin_id=admin.id)
    return settings

@router.patch("/bot", response_model=SettingsResponse)
async def update_bot_settings(
    data: BotSettingsSchema,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Обновить настройки бота"""
    service = ConfigService(db)
    settings = await service.update_settings(data.model_dump(exclude_unset=True), admin_id=admin.id)
    return settings

@router.patch("/payments", response_model=SettingsResponse)
async def update_payment_settings(
    data: PaymentSettingsSchema,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Обновить настройки платежей"""
    service = ConfigService(db)
    settings = await service.update_settings(data.model_dump(exclude_unset=True), admin_id=admin.id)
    return settings

@router.patch("/referral", response_model=SettingsResponse)
async def update_referral_settings(
    data: ReferralSettingsSchema,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Обновить настройки реферальной системы"""
    service = ConfigService(db)
    settings = await service.update_settings(data.model_dump(exclude_unset=True), admin_id=admin.id)
    return settings

@router.patch("/antifraud", response_model=SettingsResponse)
async def update_antifraud_settings(
    data: AntifraudSettingsSchema,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Обновить настройки антифрода"""
    service = ConfigService(db)
    settings = await service.update_settings(data.model_dump(exclude_unset=True), admin_id=admin.id)
    return settings

@router.patch("/notifications", response_model=SettingsResponse)
async def update_notification_settings(
    data: NotificationSettingsSchema,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Обновить настройки уведомлений"""
    service = ConfigService(db)
    settings = await service.update_settings(data.model_dump(exclude_unset=True), admin_id=admin.id)
    return settings

@router.patch("/system", response_model=SettingsResponse)
async def update_system_settings(
    data: SystemSettingsSchema,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Обновить системные настройки"""
    service = ConfigService(db)
    settings = await service.update_settings(data.model_dump(exclude_unset=True), admin_id=admin.id)
    return settings

@router.get("/payments/{provider}/config")
async def get_payment_provider_config(
    provider: str,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Получить конфигурацию конкретного платежного провайдера"""
    service = ConfigService(db)
    config = await service.get_payment_config(provider)
    if not config:
        raise HTTPException(status_code=404, detail="Provider not found")
    return config

@router.post("/payments/{provider}/test")
async def test_payment_provider(
    provider: str,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Тестовый запрос к платежному провайдеру (проверка токена)"""
    service = ConfigService(db)
    config = await service.get_payment_config(provider)

    if not config.get("enabled"):
        return {"status": "disabled", "message": "Провайдер отключен"}

    # Тестовая логика для каждого провайдера
    if provider == "cryptobot":
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://pay.crypt.bot/api/getMe",
                    headers={"Crypto-Pay-API-Token": config.get("token", "")}
                )
                if resp.status_code == 200:
                    return {"status": "ok", "message": "Токен валиден", "data": resp.json()}
                else:
                    return {"status": "error", "message": "Неверный токен", "code": resp.status_code}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    elif provider == "yookassa":
        import httpx
        import base64
        try:
            auth = base64.b64encode(f"{config.get('shop_id')}:{config.get('secret_key')}".encode()).decode()
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.yookassa.ru/v3/me",
                    headers={"Authorization": f"Basic {auth}"}
                )
                if resp.status_code == 200:
                    return {"status": "ok", "message": "Ключи валидны", "data": resp.json()}
                else:
                    return {"status": "error", "message": "Неверные ключи", "code": resp.status_code}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    elif provider == "freekassa":
        return {"status": "manual", "message": "Проверьте вручную на сайте FreeKassa"}

    return {"status": "unknown", "message": "Неизвестный провайдер"}

@router.get("/health")
async def settings_health_check(
    db: AsyncSession = Depends(get_db)
):
    """Проверка здоровья системы (публичный endpoint)"""
    service = ConfigService(db)
    s = await service.get_settings()

    return {
        "maintenance_mode": s.maintenance_mode,
        "payments_available": {
            "cryptobot": s.cryptobot_enabled and bool(s.cryptobot_token),
            "yookassa": s.yookassa_enabled and bool(s.yookassa_shop_id) and bool(s.yookassa_secret_key),
            "freekassa": s.freekassa_enabled and bool(s.freekassa_id) and bool(s.freekassa_secret),
        },
        "referral_enabled": s.referral_enabled,
        "antifraud_enabled": s.antifraud_enabled,
    }
