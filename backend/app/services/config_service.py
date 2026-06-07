"""Dynamic Configuration Service

Все настройки хранятся в PostgreSQL и кэшируются в Redis.
При изменении настройки — кэш инвалидируется.
Сервисы должны использовать get_config() вместо статического settings.
"""
import json
import os
from typing import Any, Optional, List, Dict, Union
from functools import lru_cache
from datetime import datetime

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.models.app_config import AppConfig
from app.database import async_session_maker

# Redis connection (singleton)
_redis_client: Optional[Redis] = None

async def get_redis() -> Redis:
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis_client = Redis.from_url(redis_url, decode_responses=True)
    return _redis_client


class ConfigService:
    """Управление динамическими настройками приложения"""

    CACHE_PREFIX = "gusto:config:"
    CACHE_TTL = 3600  # 1 hour

    # Default configurations (used if DB is empty or on first run)
    DEFAULTS = {
        # Brand
        "BRAND_NAME": {"value": "GUSTO VPN", "type": "str", "category": "brand", "description": "Название бренда"},
        "BRAND_TAGLINE": {"value": "Быстрый. Безопасный. Без границ.", "type": "str", "category": "brand", "description": "Слоган"},
        "SUPPORT_USERNAME": {"value": "gusto_support", "type": "str", "category": "brand", "description": "Telegram username поддержки"},
        "SUPPORT_LINK": {"value": "", "type": "str", "category": "brand", "description": "Ссылка на поддержку"},

        # Telegram
        "BOT_TOKEN": {"value": "", "type": "str", "category": "telegram", "description": "Токен Telegram бота", "is_sensitive": True},
        "ADMIN_IDS": {"value": "[]", "type": "json", "category": "telegram", "description": "Список ID администраторов (JSON массив)"},
        "WEBHOOK_URL": {"value": "", "type": "str", "category": "telegram", "description": "URL для webhook бота"},
        "WELCOME_MESSAGE": {"value": "Добро пожаловать в GUSTO VPN! 🚀", "type": "str", "category": "telegram", "description": "Приветственное сообщение"},

        # Payments — CryptoBot
        "CRYPTOBOT_ENABLED": {"value": "false", "type": "bool", "category": "payments", "description": "Включить CryptoBot"},
        "CRYPTOBOT_TOKEN": {"value": "", "type": "str", "category": "payments", "description": "Токен CryptoBot", "is_sensitive": True},
        "CRYPTOBOT_WEBHOOK_SECRET": {"value": "", "type": "str", "category": "payments", "description": "Секрет для webhook CryptoBot", "is_sensitive": True},

        # Payments — YooKassa
        "YOOKASSA_ENABLED": {"value": "false", "type": "bool", "category": "payments", "description": "Включить YooKassa"},
        "YOOKASSA_SHOP_ID": {"value": "", "type": "str", "category": "payments", "description": "Shop ID YooKassa", "is_sensitive": True},
        "YOOKASSA_SECRET_KEY": {"value": "", "type": "str", "category": "payments", "description": "Secret Key YooKassa", "is_sensitive": True},
        "YOOKASSA_WEBHOOK_SECRET": {"value": "", "type": "str", "category": "payments", "description": "Секрет для webhook YooKassa", "is_sensitive": True},

        # Payments — FreeKassa
        "FREEKASSA_ENABLED": {"value": "false", "type": "bool", "category": "payments", "description": "Включить FreeKassa"},
        "FREEKASSA_ID": {"value": "", "type": "str", "category": "payments", "description": "ID магазина FreeKassa", "is_sensitive": True},
        "FREEKASSA_SECRET": {"value": "", "type": "str", "category": "payments", "description": "Секретный ключ FreeKassa", "is_sensitive": True},
        "FREEKASSA_API_KEY": {"value": "", "type": "str", "category": "payments", "description": "API Key FreeKassa", "is_sensitive": True},
        "FREEKASSA_WEBHOOK_SECRET": {"value": "", "type": "str", "category": "payments", "description": "Секрет для webhook FreeKassa", "is_sensitive": True},

        # Payment General
        "DEFAULT_CURRENCY": {"value": "RUB", "type": "str", "category": "payments", "description": "Валюта по умолчанию"},
        "PAYMENT_TIMEOUT_MINUTES": {"value": "30", "type": "int", "category": "payments", "description": "Время жизни платежа (минут)"},

        # Referral
        "REFERRAL_ENABLED": {"value": "true", "type": "bool", "category": "referral", "description": "Включить реферальную систему"},
        "REFERRAL_LEVEL_1": {"value": "0.30", "type": "float", "category": "referral", "description": "Процент 1-го уровня (0.30 = 30%)"},
        "REFERRAL_LEVEL_2": {"value": "0.15", "type": "float", "category": "referral", "description": "Процент 2-го уровня"},
        "REFERRAL_LEVEL_3": {"value": "0.05", "type": "float", "category": "referral", "description": "Процент 3-го уровня"},
        "REFERRAL_MIN_WITHDRAW": {"value": "500", "type": "float", "category": "referral", "description": "Минимум для вывода (руб)"},

        # Anti-Fraud
        "ANTIFRAUD_ENABLED": {"value": "true", "type": "bool", "category": "security", "description": "Включить антифрод"},
        "MAX_PAYMENTS_PER_HOUR": {"value": "3", "type": "int", "category": "security", "description": "Макс. платежей в час на пользователя"},
        "MAX_UNIQUE_IPS_PER_DAY": {"value": "5", "type": "int", "category": "security", "description": "Макс. уникальных IP в день"},
        "CONFIG_SHARING_THRESHOLD": {"value": "5", "type": "int", "category": "security", "description": "Порог для детекта шаринга конфигов"},
        "AUTO_BAN_ON_SHARING": {"value": "true", "type": "bool", "category": "security", "description": "Автобан при шаринге"},

        # Smart Router
        "ROUTER_LATENCY_WEIGHT": {"value": "0.35", "type": "float", "category": "router", "description": "Вес задержки (latency)"},
        "ROUTER_LOAD_WEIGHT": {"value": "0.30", "type": "float", "category": "router", "description": "Вес нагрузки CPU"},
        "ROUTER_USERS_WEIGHT": {"value": "0.20", "type": "float", "category": "router", "description": "Вес количества пользователей"},
        "ROUTER_GEO_WEIGHT": {"value": "0.15", "type": "float", "category": "router", "description": "Вес геопозиции"},
        "MAX_LATENCY_MS": {"value": "300", "type": "int", "category": "router", "description": "Максимальная допустимая задержка (мс)"},
        "ROUTER_FALLBACK_ENABLED": {"value": "true", "type": "bool", "category": "router", "description": "Включить fallback серверы"},

        # Notifications
        "EXPIRY_NOTIFY_DAYS": {"value": "[3, 1]", "type": "json", "category": "notifications", "description": "Дни за которые уведомлять об истечении (JSON)"},
        "LOW_TRAFFIC_THRESHOLD_GB": {"value": "5.0", "type": "float", "category": "notifications", "description": "Порог трафика для уведомления (GB)"},
        "NOTIFY_PAYMENT_SUCCESS": {"value": "true", "type": "bool", "category": "notifications", "description": "Уведомлять об успешной оплате"},
        "NOTIFY_PAYMENT_FAILED": {"value": "true", "type": "bool", "category": "notifications", "description": "Уведомлять о неудачной оплате"},
        "NOTIFY_SERVER_OFFLINE": {"value": "true", "type": "bool", "category": "notifications", "description": "Уведомлять о падении сервера"},

        # Backup
        "BACKUP_ENABLED": {"value": "true", "type": "bool", "category": "backup", "description": "Включить автобэкапы"},
        "BACKUP_S3_BUCKET": {"value": "gusto-vpn-backups", "type": "str", "category": "backup", "description": "S3 bucket для бэкапов"},
        "BACKUP_S3_ENDPOINT": {"value": "", "type": "str", "category": "backup", "description": "S3 endpoint URL"},
        "BACKUP_S3_ACCESS_KEY": {"value": "", "type": "str", "category": "backup", "description": "S3 Access Key", "is_sensitive": True},
        "BACKUP_S3_SECRET_KEY": {"value": "", "type": "str", "category": "backup", "description": "S3 Secret Key", "is_sensitive": True},
        "BACKUP_RETENTION_DAYS": {"value": "30", "type": "int", "category": "backup", "description": "Срок хранения бэкапов (дней)"},
        "BACKUP_SCHEDULE": {"value": "0 3 * * *", "type": "str", "category": "backup", "description": "Расписание бэкапов (cron)"},

        # 3x-ui Monitor
        "X3UI_MONITOR_ENABLED": {"value": "true", "type": "bool", "category": "monitor", "description": "Мониторинг изменений 3x-ui"},
        "X3UI_CHECK_INTERVAL_HOURS": {"value": "6", "type": "int", "category": "monitor", "description": "Интервал проверки (часов)"},
    }

    @classmethod
    def _cache_key(cls, key: str) -> str:
        return f"{cls.CACHE_PREFIX}{key}"

    @classmethod
    def _parse_value(cls, value: str, value_type: str) -> Any:
        """Парсинг строкового значения в нужный тип"""
        if value_type == "bool":
            return value.lower() in ("true", "1", "yes", "on")
        elif value_type == "int":
            return int(value)
        elif value_type == "float":
            return float(value)
        elif value_type in ("json", "list", "dict"):
            return json.loads(value) if value else {}
        else:
            return value

    @classmethod
    def _serialize_value(cls, value: Any, value_type: str) -> str:
        """Сериализация значения в строку"""
        if value_type == "bool":
            return "true" if value else "false"
        elif value_type in ("json", "list", "dict"):
            return json.dumps(value, ensure_ascii=False)
        else:
            return str(value)

    @classmethod
    async def initialize_defaults(cls, db: AsyncSession) -> None:
        """Инициализация дефолтных настроек при первом запуске"""
        for key, meta in cls.DEFAULTS.items():
            existing = await db.execute(select(AppConfig).where(AppConfig.key == key))
            if existing.scalar_one_or_none() is None:
                config = AppConfig(
                    key=key,
                    value=meta["value"],
                    value_type=meta.get("type", "str"),
                    description=meta.get("description", ""),
                    category=meta.get("category", "general"),
                    is_sensitive=meta.get("is_sensitive", False),
                    is_editable=meta.get("is_editable", True),
                )
                db.add(config)
        await db.commit()

        # Warm cache
        await cls.warm_cache(db)

    @classmethod
    async def warm_cache(cls, db: AsyncSession) -> None:
        """Загрузка всех настроек в Redis"""
        redis = await get_redis()
        result = await db.execute(select(AppConfig))
        configs = result.scalars().all()

        pipe = redis.pipeline()
        for config in configs:
            pipe.setex(
                cls._cache_key(config.key),
                cls.CACHE_TTL,
                json.dumps({
                    "value": config.value,
                    "type": config.value_type,
                    "sensitive": config.is_sensitive,
                })
            )
        await pipe.execute()

    @classmethod
    async def get(cls, key: str, default: Any = None) -> Any:
        """Получить значение настройки (с кэша или БД)"""
        redis = await get_redis()
        cache_key = cls._cache_key(key)

        # Try cache first
        cached = await redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            return cls._parse_value(data["value"], data["type"])

        # Fallback to DB
        async with async_session_maker() as db:
            result = await db.execute(select(AppConfig).where(AppConfig.key == key))
            config = result.scalar_one_or_none()

            if config:
                # Update cache
                await redis.setex(
                    cache_key,
                    cls.CACHE_TTL,
                    json.dumps({
                        "value": config.value,
                        "type": config.value_type,
                        "sensitive": config.is_sensitive,
                    })
                )
                return cls._parse_value(config.value, config.value_type)

        # Fallback to defaults
        if key in cls.DEFAULTS:
            default_meta = cls.DEFAULTS[key]
            return cls._parse_value(default_meta["value"], default_meta.get("type", "str"))

        return default

    @classmethod
    async def get_many(cls, keys: List[str]) -> Dict[str, Any]:
        """Получить несколько настроек за один запрос"""
        redis = await get_redis()
        cache_keys = [cls._cache_key(k) for k in keys]
        cached_values = await redis.mget(cache_keys)

        result = {}
        missing_keys = []

        for i, key in enumerate(keys):
            if cached_values[i]:
                data = json.loads(cached_values[i])
                result[key] = cls._parse_value(data["value"], data["type"])
            else:
                missing_keys.append(key)

        if missing_keys:
            async with async_session_maker() as db:
                db_result = await db.execute(
                    select(AppConfig).where(AppConfig.key.in_(missing_keys))
                )
                configs = db_result.scalars().all()

                pipe = redis.pipeline()
                for config in configs:
                    result[config.key] = cls._parse_value(config.value, config.value_type)
                    pipe.setex(
                        cls._cache_key(config.key),
                        cls.CACHE_TTL,
                        json.dumps({
                            "value": config.value,
                            "type": config.value_type,
                            "sensitive": config.is_sensitive,
                        })
                    )
                await pipe.execute()

                # Fill missing with defaults
                for key in missing_keys:
                    if key not in result:
                        if key in cls.DEFAULTS:
                            default_meta = cls.DEFAULTS[key]
                            result[key] = cls._parse_value(default_meta["value"], default_meta.get("type", "str"))
                        else:
                            result[key] = None

        return result

    @classmethod
    async def get_by_category(cls, category: str, db: AsyncSession) -> List[AppConfig]:
        """Получить все настройки категории"""
        result = await db.execute(
            select(AppConfig).where(AppConfig.category == category).order_by(AppConfig.key)
        )
        return result.scalars().all()

    @classmethod
    async def get_all(cls, db: AsyncSession) -> List[AppConfig]:
        """Получить все настройки"""
        result = await db.execute(select(AppConfig).order_by(AppConfig.category, AppConfig.key))
        return result.scalars().all()

    @classmethod
    async def set(cls, key: str, value: Any, db: AsyncSession) -> AppConfig:
        """Установить значение настройки"""
        result = await db.execute(select(AppConfig).where(AppConfig.key == key))
        config = result.scalar_one_or_none()

        if config is None:
            if key not in cls.DEFAULTS:
                raise ValueError(f"Unknown config key: {key}")
            meta = cls.DEFAULTS[key]
            config = AppConfig(
                key=key,
                value_type=meta.get("type", "str"),
                description=meta.get("description", ""),
                category=meta.get("category", "general"),
                is_sensitive=meta.get("is_sensitive", False),
                is_editable=meta.get("is_editable", True),
            )
            db.add(config)

        if not config.is_editable:
            raise ValueError(f"Config key {key} is not editable")

        config.value = cls._serialize_value(value, config.value_type)
        config.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(config)

        # Invalidate cache
        redis = await get_redis()
        await redis.delete(cls._cache_key(key))

        return config

    @classmethod
    async def set_many(cls, updates: Dict[str, Any], db: AsyncSession) -> List[AppConfig]:
        """Массовое обновление настроек"""
        configs = []
        for key, value in updates.items():
            config = await cls.set(key, value, db)
            configs.append(config)
        return configs

    @classmethod
    async def reset_to_default(cls, key: str, db: AsyncSession) -> AppConfig:
        """Сбросить настройку к дефолтному значению"""
        if key not in cls.DEFAULTS:
            raise ValueError(f"Unknown config key: {key}")

        meta = cls.DEFAULTS[key]
        return await cls.set(key, cls._parse_value(meta["value"], meta.get("type", "str")), db)

    @classmethod
    async def delete(cls, key: str, db: AsyncSession) -> None:
        """Удалить кастомную настройку (только если не в DEFAULTS)"""
        if key in cls.DEFAULTS:
            raise ValueError(f"Cannot delete default config key: {key}")

        await db.execute(delete(AppConfig).where(AppConfig.key == key))
        await db.commit()

        redis = await get_redis()
        await redis.delete(cls._cache_key(key))

    @classmethod
    async def export_config(cls, db: AsyncSession, include_sensitive: bool = False) -> Dict[str, Any]:
        """Экспорт всех настроек в JSON"""
        configs = await cls.get_all(db)
        result = {}
        for config in configs:
            if config.is_sensitive and not include_sensitive:
                result[config.key] = "***REDACTED***"
            else:
                result[config.key] = cls._parse_value(config.value, config.value_type)
        return result

    @classmethod
    async def import_config(cls, data: Dict[str, Any], db: AsyncSession) -> None:
        """Импорт настроек из JSON"""
        for key, value in data.items():
            if key in cls.DEFAULTS and value != "***REDACTED***":
                await cls.set(key, value, db)


# Convenience functions for direct usage
async def get_config(key: str, default: Any = None) -> Any:
    """Короткая функция для получения конфига"""
    return await ConfigService.get(key, default)

async def get_configs(keys: List[str]) -> Dict[str, Any]:
    """Короткая функция для получения нескольких конфигов"""
    return await ConfigService.get_many(keys)
