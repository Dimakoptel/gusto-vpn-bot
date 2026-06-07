"""
System Settings Model
Все настройки проекта хранятся в БД и управляются через админ-панель
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, JSON
from sqlalchemy.sql import func
from backend.app.database import Base

class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)

    # === BOT SETTINGS ===
    bot_token = Column(Text, nullable=True, comment="Telegram Bot Token")
    admin_ids = Column(JSON, default=[], comment="Список ID администраторов Telegram")
    support_username = Column(String(255), nullable=True, comment="@username поддержки")
    welcome_message = Column(Text, nullable=True, comment="Приветственное сообщение")

    # === PAYMENT SETTINGS ===
    # CryptoBot
    cryptobot_token = Column(Text, nullable=True)
    cryptobot_enabled = Column(Boolean, default=False)

    # YooKassa
    yookassa_shop_id = Column(String(255), nullable=True)
    yookassa_secret_key = Column(Text, nullable=True)
    yookassa_enabled = Column(Boolean, default=False)
    yookassa_fiscal_enabled = Column(Boolean, default=False)

    # FreeKassa
    freekassa_id = Column(String(255), nullable=True)
    freekassa_secret = Column(Text, nullable=True)
    freekassa_api_key = Column(Text, nullable=True)
    freekassa_enabled = Column(Boolean, default=False)

    # === REFERRAL SETTINGS ===
    referral_enabled = Column(Boolean, default=True)
    referral_level1_percent = Column(Float, default=30.0)
    referral_level2_percent = Column(Float, default=15.0)
    referral_level3_percent = Column(Float, default=5.0)
    referral_min_payout = Column(Float, default=500.0)

    # === ANTIFRAUD SETTINGS ===
    antifraud_enabled = Column(Boolean, default=True)
    antifraud_max_ips = Column(Integer, default=3)
    antifraud_max_countries = Column(Integer, default=2)
    antifraud_ban_hours = Column(Integer, default=24)

    # === NOTIFICATION SETTINGS ===
    notify_expiry_3days = Column(Boolean, default=True)
    notify_expiry_1day = Column(Boolean, default=True)
    notify_expiry_today = Column(Boolean, default=True)
    notify_low_traffic_gb = Column(Float, default=5.0)
    notify_channel_id = Column(String(255), nullable=True)

    # === SYSTEM SETTINGS ===
    app_name = Column(String(255), default="GUSTO VPN")
    app_logo_url = Column(Text, nullable=True)
    maintenance_mode = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(Integer, nullable=True, comment="ID админа, последнего изменившего")

    @classmethod
    def get_defaults(cls):
        """Возвращает настройки по умолчанию"""
        return {
            "bot_token": "",
            "admin_ids": [],
            "support_username": "",
            "welcome_message": "Добро пожаловать в GUSTO VPN! 🚀",
            "cryptobot_enabled": False,
            "yookassa_enabled": False,
            "freekassa_enabled": False,
            "referral_enabled": True,
            "referral_level1_percent": 30.0,
            "referral_level2_percent": 15.0,
            "referral_level3_percent": 5.0,
            "referral_min_payout": 500.0,
            "antifraud_enabled": True,
            "antifraud_max_ips": 3,
            "antifraud_max_countries": 2,
            "antifraud_ban_hours": 24,
            "notify_expiry_3days": True,
            "notify_expiry_1day": True,
            "notify_expiry_today": True,
            "notify_low_traffic_gb": 5.0,
            "app_name": "GUSTO VPN",
            "maintenance_mode": False,
        }
