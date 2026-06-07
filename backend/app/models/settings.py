"""SystemSettings Model — все настройки в одной таблице"""
from sqlalchemy import Column, Integer, String, Boolean, Float, Text, DateTime, JSON
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.database import Base

class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True)

    # Bot settings
    bot_token = Column(Text)
    admin_ids = Column(JSONB, default=list)
    support_username = Column(String(255))
    welcome_message = Column(Text, default="Добро пожаловать в GUSTO VPN! 🚀")

    # Payment providers
    cryptobot_token = Column(Text)
    cryptobot_enabled = Column(Boolean, default=False)
    yookassa_shop_id = Column(String(255))
    yookassa_secret_key = Column(Text)
    yookassa_enabled = Column(Boolean, default=False)
    yookassa_fiscal_enabled = Column(Boolean, default=False)
    freekassa_id = Column(String(255))
    freekassa_secret = Column(Text)
    freekassa_api_key = Column(Text)
    freekassa_enabled = Column(Boolean, default=False)

    # Referral system
    referral_enabled = Column(Boolean, default=True)
    referral_level1_percent = Column(Float, default=30.0)
    referral_level2_percent = Column(Float, default=15.0)
    referral_level3_percent = Column(Float, default=5.0)
    referral_min_payout = Column(Float, default=500.0)

    # Antifraud
    antifraud_enabled = Column(Boolean, default=True)
    antifraud_max_ips = Column(Integer, default=3)
    antifraud_max_countries = Column(Integer, default=2)
    antifraud_ban_hours = Column(Integer, default=24)

    # Notifications
    notify_expiry_3days = Column(Boolean, default=True)
    notify_expiry_1day = Column(Boolean, default=True)
    notify_expiry_today = Column(Boolean, default=True)
    notify_low_traffic_gb = Column(Float, default=5.0)
    notify_channel_id = Column(String(255))

    # System
    app_name = Column(String(255), default="GUSTO VPN")
    app_logo_url = Column(String(500))
    maintenance_mode = Column(Boolean, default=False)

    # Metadata
    updated_by = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get_defaults(cls):
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
