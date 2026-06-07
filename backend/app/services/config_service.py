"""
Config Service
Читает настройки из БД (SystemSettings) с кэшированием в Redis
"""
import json
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.settings import SystemSettings
from backend.app.cache import redis_client

CACHE_KEY = "system_settings"
CACHE_TTL = 300  # 5 минут

class ConfigService:
    def __init__(self, db: Session):
        self.db = db
        self._cache = None

    def _get_from_cache(self) -> Optional[Dict[str, Any]]:
        try:
            data = redis_client.get(CACHE_KEY)
            if data:
                return json.loads(data)
        except Exception:
            pass
        return None

    def _set_cache(self, data: Dict[str, Any]):
        try:
            redis_client.setex(CACHE_KEY, CACHE_TTL, json.dumps(data))
        except Exception:
            pass

    def _invalidate_cache(self):
        try:
            redis_client.delete(CACHE_KEY)
        except Exception:
            pass

    def get_settings(self) -> SystemSettings:
        """Получить или создать настройки по умолчанию"""
        settings = self.db.query(SystemSettings).first()
        if not settings:
            defaults = SystemSettings.get_defaults()
            settings = SystemSettings(**defaults)
            self.db.add(settings)
            self.db.commit()
            self.db.refresh(settings)
        return settings

    def get_dict(self) -> Dict[str, Any]:
        """Получить настройки как словарь (с кэшем)"""
        cached = self._get_from_cache()
        if cached:
            return cached

        settings = self.get_settings()
        data = {
            c.name: getattr(settings, c.name)
            for c in settings.__table__.columns
            if c.name not in ("id", "created_at", "updated_at", "updated_by")
        }
        self._set_cache(data)
        return data

    def update_settings(self, data: Dict[str, Any], admin_id: Optional[int] = None) -> SystemSettings:
        """Обновить настройки"""
        settings = self.get_settings()

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

        self.db.commit()
        self.db.refresh(settings)
        self._invalidate_cache()
        return settings

    # === Convenience methods ===
    def get_bot_token(self) -> str:
        return self.get_settings().bot_token or ""

    def get_admin_ids(self) -> List[int]:
        return self.get_settings().admin_ids or []

    def is_admin(self, telegram_id: int) -> bool:
        return telegram_id in self.get_admin_ids()

    def get_payment_config(self, provider: str) -> Dict[str, Any]:
        s = self.get_settings()
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

    def get_referral_config(self) -> Dict[str, Any]:
        s = self.get_settings()
        return {
            "enabled": s.referral_enabled,
            "levels": [s.referral_level1_percent, s.referral_level2_percent, s.referral_level3_percent],
            "min_payout": s.referral_min_payout,
        }

    def get_antifraud_config(self) -> Dict[str, Any]:
        s = self.get_settings()
        return {
            "enabled": s.antifraud_enabled,
            "max_ips": s.antifraud_max_ips,
            "max_countries": s.antifraud_max_countries,
            "ban_hours": s.antifraud_ban_hours,
        }

    def get_notification_config(self) -> Dict[str, Any]:
        s = self.get_settings()
        return {
            "expiry_3days": s.notify_expiry_3days,
            "expiry_1day": s.notify_expiry_1day,
            "expiry_today": s.notify_expiry_today,
            "low_traffic_gb": s.notify_low_traffic_gb,
            "channel_id": s.notify_channel_id,
        }
