"""GUSTO Payment Model"""
from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, DateTime, Numeric, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
import enum
from datetime import datetime
from app.database import Base


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethod(str, enum.Enum):
    CRYPTOBOT = "cryptobot"
    YOOKASSA = "yookassa"
    FREEKASSA = "freekassa"
    REFERRAL = "referral_balance"


class GustoPayment(Base):
    __tablename__ = "gusto_payments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("gusto_users.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("gusto_subscriptions.id"), nullable=True)

    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="RUB")

    method = Column(SQLEnum(PaymentMethod), nullable=False)
    provider_payment_id = Column(String(255))
    provider_data = Column(JSONB)

    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING)
    paid_at = Column(DateTime)

    referral_processed = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("GustoUser", back_populates="payments")
    subscription = relationship("GustoSubscription")
