"""
GUSTO VPN Configuration
Быстрый. Безопасный. Без границ.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List, Dict
import json


class GustoSettings(BaseSettings):
    """Настройки GUSTO VPN Bot"""

    # Brand
    BRAND_NAME: str = "GUSTO VPN"
    BRAND_TAGLINE: str = "Быстрый. Безопасный. Без границ."
    SUPPORT_USERNAME: str = "gusto_support"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://gusto:gusto_secret@localhost:5432/gustovpn"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "gusto-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Telegram
    BOT_TOKEN: str = ""
    ADMIN_IDS: List[int] = []
    WEBHOOK_URL: str = ""

    # 3x-ui Panels
    X3UI_PANELS: str = "[]"

    @property
    def x3ui_panels(self) -> List[Dict]:
        return json.loads(self.X3UI_PANELS)

    # Payment Providers
    CRYPTOBOT_TOKEN: str = ""
    YOOKASSA_SHOP_ID: str = ""
    YOOKASSA_SECRET_KEY: str = ""
    FREEKASSA_ID: str = ""
    FREEKASSA_SECRET: str = ""

    # Referral System
    REFERRAL_LEVELS: Dict[int, float] = {1: 0.30, 2: 0.15, 3: 0.05}
    REFERRAL_MIN_WITHDRAW: float = 500.0

    # Anti-Fraud
    MAX_PAYMENTS_PER_HOUR: int = 3
    MAX_UNIQUE_IPS_PER_DAY: int = 5
    CONFIG_SHARING_THRESHOLD: int = 5

    # Backup
    BACKUP_S3_BUCKET: str = "gusto-vpn-backups"
    BACKUP_S3_ENDPOINT: str = ""
    BACKUP_RETENTION_DAYS: int = 30

    # Smart Router
    ROUTER_LATENCY_WEIGHT: float = 0.35
    ROUTER_LOAD_WEIGHT: float = 0.30
    ROUTER_USERS_WEIGHT: float = 0.20
    ROUTER_GEO_WEIGHT: float = 0.15
    MAX_LATENCY_MS: int = 300

    # Notifications
    EXPIRY_NOTIFY_DAYS: List[int] = [3, 1]
    LOW_TRAFFIC_THRESHOLD_GB: float = 5.0

    class Config:
        env_file = ".env"
        env_prefix = "GUSTO_"


@lru_cache()
def get_settings() -> GustoSettings:
    return GustoSettings()


settings = get_settings()
