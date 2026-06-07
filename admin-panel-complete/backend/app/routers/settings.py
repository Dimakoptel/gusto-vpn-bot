"""Admin Settings API — управление всеми настройками через веб-панель"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.app_config import AppConfig
from app.services.config_service import ConfigService

router = APIRouter(prefix="/api/settings", tags=["Settings"])


class ConfigItemResponse(BaseModel):
    key: str
    value: Any
    value_type: str
    description: str
    category: str
    is_sensitive: bool
    is_editable: bool
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class ConfigUpdateRequest(BaseModel):
    key: str
    value: Any


class BulkConfigUpdateRequest(BaseModel):
    settings: Dict[str, Any] = Field(..., description="Ключ-значение для массового обновления")


class CategoryResponse(BaseModel):
    category: str
    label: str
    icon: str
    description: str


CATEGORIES = [
    CategoryResponse(category="brand", label="Бренд", icon="Palette", description="Название, слоган, поддержка"),
    CategoryResponse(category="telegram", label="Telegram", icon="MessageCircle", description="Бот, токены, админы"),
    CategoryResponse(category="payments", label="Платежи", icon="CreditCard", description="Провайдеры, токены, валюта"),
    CategoryResponse(category="referral", label="Реферальная система", icon="Users", description="Проценты, минимумы"),
    CategoryResponse(category="security", label="Безопасность", icon="Shield", description="Антифрод, лимиты"),
    CategoryResponse(category="router", label="Smart Router", icon="Route", description="Веса, latency, fallback"),
    CategoryResponse(category="notifications", label="Уведомления", icon="Bell", description="Уведомления пользователям"),
    CategoryResponse(category="backup", label="Бэкапы", icon="Database", description="S3, расписание, хранение"),
    CategoryResponse(category="monitor", label="Мониторинг", icon="Activity", description="3x-ui, интервалы"),
]


def _mask_sensitive(config: AppConfig) -> AppConfig:
    """Маскируем чувствительные значения для ответа"""
    if config.is_sensitive and config.value:
        config.value = "•" * min(len(config.value), 20)
    return config


@router.get("/categories", response_model=List[CategoryResponse])
async def get_categories():
    """Получить список категорий настроек"""
    return CATEGORIES


@router.get("/", response_model=List[ConfigItemResponse])
async def get_all_settings(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Получить все настройки (опционально по категории)"""
    if category:
        configs = await ConfigService.get_by_category(category, db)
    else:
        configs = await ConfigService.get_all(db)

    # Initialize defaults if empty
    if not configs:
        await ConfigService.initialize_defaults(db)
        configs = await ConfigService.get_all(db)

    result = []
    for config in configs:
        masked = _mask_sensitive(config)
        result.append(ConfigItemResponse(
            key=masked.key,
            value=ConfigService._parse_value(masked.value, masked.value_type),
            value_type=masked.value_type,
            description=masked.description,
            category=masked.category,
            is_sensitive=masked.is_sensitive,
            is_editable=masked.is_editable,
            updated_at=masked.updated_at.isoformat() if masked.updated_at else None,
        ))
    return result


@router.get("/{key}", response_model=ConfigItemResponse)
async def get_setting(key: str, db: AsyncSession = Depends(get_db)):
    """Получить одну настройку по ключу"""
    from sqlalchemy import select
    result = await db.execute(select(AppConfig).where(AppConfig.key == key))
    config = result.scalar_one_or_none()

    if not config:
        if key in ConfigService.DEFAULTS:
            meta = ConfigService.DEFAULTS[key]
            return ConfigItemResponse(
                key=key,
                value=ConfigService._parse_value(meta["value"], meta.get("type", "str")),
                value_type=meta.get("type", "str"),
                description=meta.get("description", ""),
                category=meta.get("category", "general"),
                is_sensitive=meta.get("is_sensitive", False),
                is_editable=meta.get("is_editable", True),
            )
        raise HTTPException(status_code=404, detail=f"Setting {key} not found")

    masked = _mask_sensitive(config)
    return ConfigItemResponse(
        key=masked.key,
        value=ConfigService._parse_value(masked.value, masked.value_type),
        value_type=masked.value_type,
        description=masked.description,
        category=masked.category,
        is_sensitive=masked.is_sensitive,
        is_editable=masked.is_editable,
        updated_at=masked.updated_at.isoformat() if masked.updated_at else None,
    )


@router.put("/{key}", response_model=ConfigItemResponse)
async def update_setting(
    key: str,
    value: Any = Body(..., embed=True),
    db: AsyncSession = Depends(get_db)
):
    """Обновить одну настройку"""
    try:
        config = await ConfigService.set(key, value, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ConfigItemResponse(
        key=config.key,
        value=ConfigService._parse_value(config.value, config.value_type),
        value_type=config.value_type,
        description=config.description,
        category=config.category,
        is_sensitive=config.is_sensitive,
        is_editable=config.is_editable,
        updated_at=config.updated_at.isoformat() if config.updated_at else None,
    )


@router.put("/", response_model=List[ConfigItemResponse])
async def bulk_update_settings(
    request: BulkConfigUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Массовое обновление настроек"""
    configs = await ConfigService.set_many(request.settings, db)

    result = []
    for config in configs:
        result.append(ConfigItemResponse(
            key=config.key,
            value=ConfigService._parse_value(config.value, config.value_type),
            value_type=config.value_type,
            description=config.description,
            category=config.category,
            is_sensitive=config.is_sensitive,
            is_editable=config.is_editable,
            updated_at=config.updated_at.isoformat() if config.updated_at else None,
        ))
    return result


@router.post("/{key}/reset")
async def reset_setting(key: str, db: AsyncSession = Depends(get_db)):
    """Сбросить настройку к дефолтному значению"""
    try:
        config = await ConfigService.reset_to_default(key, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status": "reset", "key": config.key, "value": ConfigService._parse_value(config.value, config.value_type)}


@router.post("/initialize")
async def initialize_defaults(db: AsyncSession = Depends(get_db)):
    """Инициализация дефолтных настроек (используется при первом запуске)"""
    await ConfigService.initialize_defaults(db)
    return {"status": "initialized", "count": len(ConfigService.DEFAULTS)}


@router.get("/export/json")
async def export_settings(
    include_sensitive: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Экспорт всех настроек в JSON"""
    data = await ConfigService.export_config(db, include_sensitive=include_sensitive)
    return {
        "exported_at": datetime.utcnow().isoformat(),
        "settings": data,
    }


@router.post("/import/json")
async def import_settings(
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Импорт настроек из JSON"""
    settings_data = data.get("settings", data)
    await ConfigService.import_config(settings_data, db)
    return {"status": "imported", "count": len(settings_data)}


from datetime import datetime
