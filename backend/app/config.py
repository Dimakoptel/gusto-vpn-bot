"""GUSTO Configuration"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache

class CoreSettings(BaseSettings):
    """Core settings loaded from environment"""
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/gusto"
    REDIS_URL: str = "redis://redis:6379/0"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    CORS_ORIGINS: str = "*"

    # Router defaults
    ROUTER_LATENCY_WEIGHT: float = 0.35
    ROUTER_LOAD_WEIGHT: float = 0.30
    ROUTER_USERS_WEIGHT: float = 0.20
    ROUTER_GEO_WEIGHT: float = 0.15
    MAX_LATENCY_MS: float = 300.0

    # Referral defaults
    REFERRAL_LEVELS: dict = {1: 0.30, 2: 0.15, 3: 0.05}
    REFERRAL_MIN_WITHDRAW: float = 500.0

    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache()
def get_core_settings():
    return CoreSettings()

core_settings = get_core_settings()
# Backwards compatibility: some modules import `settings`
settings = core_settings

class DynamicSettingsProxy:
    """Proxy для динамических настроек из БД"""

    async def get(self, key: str, default=None):
        from app.services.config_service import ConfigService
        return await ConfigService.get(key, default)

    async def get_many(self, keys: list):
        from app.services.config_service import ConfigService
        return await ConfigService.get_many(keys)

dynamic_settings = DynamicSettingsProxy()
