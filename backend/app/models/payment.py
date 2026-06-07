"""Payment Model — GustoPayment"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.database import Base
import enum

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"

class PaymentMethod(str, enum.Enum):
    CRYPTOBOT = "cryptobot"
    YOOKASSA = "yookassa"
    FREEKASSA = "freekassa"
    MANUAL = "manual"

class GustoPayment(Base):
    __tablename__ = "gusto_payments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("gusto_users.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("gusto_subscriptions.id"))
    plan_id = Column(Integer, ForeignKey("gusto_plans.id"))

    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="RUB")
    method = Column(Enum(PaymentMethod), nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)

    provider_payment_id = Column(String(255))
    provider_data = Column(JSONB, default=dict)

    paid_at = Column(DateTime)
    refunded_at = Column(DateTime)
    refund_amount = Column(Float)
    refund_reason = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
