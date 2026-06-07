"""GUSTO Subscription Model"""
from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, DateTime, Numeric, Boolean, Text, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum
from datetime import datetime
from app.database import Base


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    PENDING = "pending"


class GustoSubscription(Base):
    __tablename__ = "gusto_subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("gusto_users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("gusto_plans.id"), nullable=False)
    server_id = Column(Integer, ForeignKey("gusto_servers.id"), nullable=False)

    email = Column(String(255), unique=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True)
    inbound_id = Column(Integer)

    protocol = Column(String(20), default="vless")
    security = Column(String(20), default="reality")

    total_gb = Column(Numeric(10, 2), default=100)
    used_gb = Column(Numeric(10, 2), default=0)
    device_limit = Column(Integer, default=3)
    ip_limit = Column(Integer, default=0)

    started_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)

    auto_renew = Column(Boolean, default=False)
    renew_plan_id = Column(Integer, ForeignKey("gusto_plans.id"), nullable=True)

    config_link = Column(Text)
    config_json = Column(JSONB)
    qr_data = Column(Text)

    unique_ips_24h = Column(Integer, default=0)
    last_ip_check = Column(DateTime)

    user = relationship("GustoUser", back_populates="subscriptions")
    plan = relationship("GustoPlan", foreign_keys=[plan_id])
    server = relationship("GustoServer")
    renew_plan = relationship("GustoPlan", foreign_keys=[renew_plan_id])
