"""Gusto Plan Model — тарифные планы"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, Enum
from sqlalchemy.dialects.postgresql import JSONB
import enum
from datetime import datetime
from app.database import Base

class PlanDuration(str, enum.Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMIANNUAL = "semiannual"
    ANNUAL = "annual"
    CUSTOM = "custom"

class GustoPlan(Base):
    __tablename__ = "gusto_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)

    # Pricing
    price = Column(Float, nullable=False)
    currency = Column(String(3), default="RUB")

    # Traffic & Duration
    traffic_gb = Column(Float, default=100)
    duration_days = Column(Integer, default=30)
    duration_type = Column(Enum(PlanDuration), default=PlanDuration.MONTHLY)

    # Features
    device_limit = Column(Integer, default=3)
    ip_limit = Column(Integer, default=0)
    protocol = Column(String(20), default="vless")
    security = Column(String(20), default="reality")

    # Limits
    speed_mbps = Column(Integer, default=100)
    is_premium = Column(Boolean, default=False)
    is_popular = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)

    # Metadata
    features = Column(JSONB, default=list)
    target_countries = Column(JSONB, default=list)

    # Referral discount
    referral_discount_percent = Column(Float, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def price_per_day(self) -> float:
        return self.price / self.duration_days if self.duration_days > 0 else 0

    @property
    def price_per_gb(self) -> float:
        return self.price / self.traffic_gb if self.traffic_gb > 0 else 0
