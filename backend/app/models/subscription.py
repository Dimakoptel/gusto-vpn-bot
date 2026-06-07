"""Subscription Model — GustoSubscription"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.database import Base
import enum

class SubscriptionStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class GustoSubscription(Base):
    __tablename__ = "gusto_subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("gusto_users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("gusto_plans.id"), nullable=False)
    server_id = Column(Integer, ForeignKey("gusto_servers.id"), nullable=False)

    email = Column(String(255), nullable=False)
    uuid = Column(String(36), nullable=False)
    inbound_id = Column(Integer, default=1)
    protocol = Column(String(20), default="vless")
    security = Column(String(20), default="reality")
    flow = Column(String(50), default="xtls-rprx-vision")

    total_gb = Column(Float, default=100.0)
    used_gb = Column(Float, default=0.0)
    device_limit = Column(Integer, default=3)
    ip_limit = Column(Integer, default=3)
    unique_ips_24h = Column(Integer, default=0)
    last_ip_check = Column(DateTime)

    started_at = Column(DateTime)
    expires_at = Column(DateTime)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.PENDING)

    config_link = Column(Text)
    config_json = Column(JSONB, default=dict)

    notified_3days = Column(Boolean, default=False)
    notified_1day = Column(Boolean, default=False)
    notified_today = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
