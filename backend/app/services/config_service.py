"""
Config Service — Async version
Читает настройки из БД (SystemSettings) с кэшированием в Redis
"""
import json
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.settings import SystemSettings
from app.database import AsyncSessionLocal

logger = logging.getLogger("gusto.config")

CACHE_KEY = "system_settings"
CACHE_TTL = 300  # 5 минут

# Singleton instance for non-async contexts
_config_cache: Optional[Dict[str, Any]] = None

class ConfigService:
    """Async ConfigService — инстанцируется с db сессией"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_from_cache(self) -> Optional[Dict[str, Any]]:
        """Получить из Redis cache (если доступен)"""
        try:
            from app.database import redis_client
            data = await redis_client.get(CACHE_KEY)
            if data:
                return json.loads(data)
        except Exception:
            pass
        return None

    async def _set_cache(self, data: Dict[str, Any]):
        """Сохранить в Redis cache"""
        try:
            from app.database import redis_client
            await redis_client.setex(CACHE_KEY, CACHE_TTL, json.dumps(data))
        except Exception:
            pass

    async def _invalidate_cache(self):
        """Инвалидировать кэш"""
        try:
            from app.database import redis_client
            await redis_client.delete(CACHE_KEY)
        except Exception:
            pass

    async def get_settings(self) -> SystemSettings:
        """Получить или создать настройки по умолчанию"""
        result = await self.db.execute(select(SystemSettings))
        settings = result.scalar_one_or_none()

        if not settings:
            defaults = SystemSettings.get_defaults()
            settings = SystemSettings(**defaults)
            self.db.add(settings)
            await self.db.commit()
            await self.db.refresh(settings)
            logger.info("✅ Created default system settings")

        return settings

    async def get_dict(self) -> Dict[str, Any]:
        """Получить настройки как словарь (с кэшем)"""
        cached = await self._get_from_cache()
        if cached:
            return cached

        settings = await self.get_settings()
        data = {
            c.name: getattr(settings, c.name)
            for c in settings.__table__.columns
            if c.name not in ("id", "created_at", "updated_at", "updated_by")
        }
        await self._set_cache(data)
        return data

    async def update_settings(self, data: Dict[str, Any], admin_id: Optional[int] = None) -> SystemSettings:
        """Обновить настройки"""
        settings = await self.get_settings()

        allowed_fields = [
            "bot_token", "admin_ids", "support_username", "welcome_message",
            "cryptobot_token", "cryptobot_enabled",
            "yookassa_shop_id", "yookassa_secret_key", "yookassa_enabled", "yookassa_fiscal_enabled",
            "freekassa_id", "freekassa_secret", "freekassa_api_key", "freekassa_enabled",
            "referral_enabled", "referral_level1_percent", "referral_level2_percent",
            "referral_level3_percent", "referral_min_payout",
            "antifraud_enabled", "antifraud_max_ips", "antifraud_max_countries", "antifraud_ban_hours",
            "notify_expiry_3days", "notify_expiry_1day", "notify_expiry_today",
            "notify_low_traffic_gb", "notify_channel_id",
            "app_name", "app_logo_url", "maintenance_mode",
        ]

        for key, value in data.items():
            if key in allowed_fields and hasattr(settings, key):
                setattr(settings, key, value)

        if admin_id:
            settings.updated_by = admin_id

        await self.db.commit()
        await self.db.refresh(settings)
        await self._invalidate_cache()
        return settings

    # === Convenience methods ===
    async def get_bot_token(self) -> str:
        s = await self.get_settings()
        return s.bot_token or ""

    async def get_admin_ids(self) -> List[int]:
        s = await self.get_settings()
        return s.admin_ids or []

    async def is_admin(self, telegram_id: int) -> bool:
        return telegram_id in await self.get_admin_ids()

    async def get_payment_config(self, provider: str) -> Dict[str, Any]:
        s = await self.get_settings()
        configs = {
            "cryptobot": {
                "token": s.cryptobot_token,
                "enabled": s.cryptobot_enabled,
            },
            "yookassa": {
                "shop_id": s.yookassa_shop_id,
                "secret_key": s.yookassa_secret_key,
                "enabled": s.yookassa_enabled,
                "fiscal_enabled": s.yookassa_fiscal_enabled,
            },
            "freekassa": {
                "id": s.freekassa_id,
                "secret": s.freekassa_secret,
                "api_key": s.freekassa_api_key,
                "enabled": s.freekassa_enabled,
            },
        }
        return configs.get(provider, {})

    async def get_referral_config(self) -> Dict[str, Any]:
        s = await self.get_settings()
        return {
            "enabled": s.referral_enabled,
            "levels": [s.referral_level1_percent, s.referral_level2_percent, s.referral_level3_percent],
            "min_payout": s.referral_min_payout,
        }

    async def get_antifraud_config(self) -> Dict[str, Any]:
        s = await self.get_settings()
        return {
            "enabled": s.antifraud_enabled,
            "max_ips": s.antifraud_max_ips,
            "max_countries": s.antifraud_max_countries,
            "ban_hours": s.antifraud_ban_hours,
        }

    async def get_notification_config(self) -> Dict[str, Any]:
        s = await self.get_settings()
        return {
            "expiry_3days": s.notify_expiry_3days,
            "expiry_1day": s.notify_expiry_1day,
            "expiry_today": s.notify_expiry_today,
            "low_traffic_gb": s.notify_low_traffic_gb,
            "channel_id": s.notify_channel_id,
        }

    # === Class methods for singleton-like access (used by dynamic_settings) ===
    @classmethod
    async def get(cls, key: str, default: Any = None) -> Any:
        """Получить одну настройку (singleton pattern)"""
        async with AsyncSessionLocal() as db:
            service = cls(db)
            settings = await service.get_settings()
            return getattr(settings, key, default)

    @classmethod
    async def get_many(cls, keys: List[str]) -> Dict[str, Any]:
        """Получить несколько настроек"""
        async with AsyncSessionLocal() as db:
            service = cls(db)
            settings = await service.get_settings()
            return {k: getattr(settings, k, None) for k in keys if hasattr(settings, k)}

    @classmethod
    async def initialize_defaults(cls, db: AsyncSession):
        """Инициализировать настройки по умолчанию (вызывается из main.py lifespan)"""
        service = cls(db)
        await service.get_settings()  # Создаст если не существует
        logger.info("✅ System settings initialized")
