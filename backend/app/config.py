"""GUSTO VPN Dynamic Configuration

Все настройки теперь управляются через админ-панель и хранятся в БД.
Этот файл предоставляет fallback на .env для критичных параметров (DB URL, SECRET_KEY)
и динамический доступ к остальным настройкам через ConfigService.
"""
import os
from typing import List, Dict, Any
from functools import lru_cache

from pydantic_settings import BaseSettings


class CoreSettings(BaseSettings):
    """Критичные настройки, которые должны быть в .env (не редактируются через админ-панель)"""

    # Database & Redis — критично, не меняется через панель
    DATABASE_URL: str = "postgresql+asyncpg://gusto:gusto_secret@localhost:5432/gustovpn"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security — критично
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Admin panel auth (separate from bot admins)
    ADMIN_PANEL_USERNAME: str = "admin"
    ADMIN_PANEL_PASSWORD: str = "admin"  # Change in production!

    class Config:
        env_file = ".env"
        env_prefix = "GUSTO_"


@lru_cache()
def get_core_settings() -> CoreSettings:
    return CoreSettings()


core_settings = get_core_settings()


# Dynamic settings accessor (for non-async contexts)
# Use ConfigService.get() in async contexts instead
class DynamicSettingsProxy:
    """Прокси для доступа к динамическим настройкам.

    Использование:
        from app.config import dynamic_settings
        value = await dynamic_settings.get("BOT_TOKEN")

    Или в async коде:
        from app.services.config_service import get_config
        value = await get_config("BOT_TOKEN")
    """

    @staticmethod
    async def get(key: str, default: Any = None) -> Any:
        from app.services.config_service import ConfigService
        return await ConfigService.get(key, default)

    @staticmethod
    async def get_many(keys: List[str]) -> Dict[str, Any]:
        from app.services.config_service import ConfigService
        return await ConfigService.get_many(keys)

    @staticmethod
    async def get_bool(key: str, default: bool = False) -> bool:
        val = await DynamicSettingsProxy.get(key, default)
        if isinstance(val, bool):
            return val
        return str(val).lower() in ("true", "1", "yes", "on")

    @staticmethod
    async def get_int(key: str, default: int = 0) -> int:
        val = await DynamicSettingsProxy.get(key, default)
        return int(val) if val is not None else default

    @staticmethod
    async def get_float(key: str, default: float = 0.0) -> float:
        val = await DynamicSettingsProxy.get(key, default)
        return float(val) if val is not None else default

    @staticmethod
    async def get_list(key: str, default: List = None) -> List:
        import json
        val = await DynamicSettingsProxy.get(key, default or [])
        if isinstance(val, str):
            return json.loads(val)
        return val if isinstance(val, list) else [val]


dynamic_settings = DynamicSettingsProxy()
