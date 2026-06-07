"""GUSTO User Model"""
import uuid
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class GustoUser(Base):
    __tablename__ = "gusto_users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    phone = Column(String(20))
    language = Column(String(10), default="ru")

    country_code = Column(String(5))
    reg_ip = Column(INET)

    referral_code = Column(String(16), unique=True, default=lambda: str(uuid.uuid4())[:8])
    referred_by = Column(Integer, ForeignKey("gusto_users.id"), nullable=True)
    referral_balance = Column(Numeric(10, 2), default=0)
    total_earned = Column(Numeric(10, 2), default=0)
    referral_level = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)
    is_banned = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    is_vip = Column(Boolean, default=False)

    achievements = Column(JSONB, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)

    subscriptions = relationship("GustoSubscription", back_populates="user")
    payments = relationship("GustoPayment", back_populates="user")
    referrals = relationship("GustoUser", backref="referrer", remote_side=[id])
