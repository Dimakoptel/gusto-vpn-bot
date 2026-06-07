"""User Model — GustoUser"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, BigInteger, Float, ForeignKey
from sqlalchemy.dialects.postgresql import INET, JSONB
from datetime import datetime
from app.database import Base

class GustoUser(Base):
    __tablename__ = "gusto_users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    language = Column(String(10), default="ru")
    country_code = Column(String(5), default="RU")

    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    ban_reason = Column(Text)
    banned_at = Column(DateTime)

    referred_by = Column(Integer, ForeignKey("gusto_users.id"), nullable=True)
    referral_code = Column(String(20), unique=True)
    referral_level = Column(Integer, default=0)
    referral_balance = Column(Float, default=0.0)
    total_earned = Column(Float, default=0.0)
    referral_count = Column(Integer, default=0)

    last_ip = Column(INET)
    last_country = Column(String(5))
    unique_ips_24h = Column(JSONB, default=list)
    total_logins = Column(Integer, default=0)
    last_login = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
