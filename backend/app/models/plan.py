"""Plan Model — GustoPlan"""
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, Enum
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.database import Base
import enum

class PlanDuration(str, enum.Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    LIFETIME = "lifetime"

class GustoPlan(Base):
    __tablename__ = "gusto_plans"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)

    price = Column(Float, nullable=False)
    duration_days = Column(Integer, nullable=False)
    traffic_gb = Column(Float, nullable=False)
    speed_mbps = Column(Integer, default=100)
    device_limit = Column(Integer, default=3)
    ip_limit = Column(Integer, default=3)

    protocol = Column(String(20), default="vless")
    security = Column(String(20), default="reality")
    flow = Column(String(50), default="xtls-rprx-vision")

    is_active = Column(Boolean, default=True)
    is_premium = Column(Boolean, default=False)
    is_popular = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)

    features = Column(JSONB, default=list)
    target_countries = Column(JSONB, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
