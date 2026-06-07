"""GUSTO Server Model — 3x-ui nodes"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.database import Base


class GustoServer(Base):
    __tablename__ = "gusto_servers"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    display_name = Column(String(255))
    location = Column(String(100))
    country_code = Column(String(5))
    region = Column(String(50))
    flag_emoji = Column(String(10))

    host = Column(String(255), nullable=False)
    port = Column(Integer, default=54321)
    api_port = Column(Integer, default=443)
    panel_username = Column(String(255))
    panel_password = Column(Text)

    is_active = Column(Boolean, default=True)
    is_online = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    last_check = Column(DateTime, default=datetime.utcnow)

    cpu_load = Column(Float, default=0)
    memory_used = Column(Float, default=0)
    memory_total = Column(Float, default=0)
    disk_used = Column(Float, default=0)
    network_in = Column(BigInteger, default=0)
    network_out = Column(BigInteger, default=0)
    total_users = Column(Integer, default=0)
    max_users = Column(Integer, default=500)
    xray_version = Column(String(20))

    reality_private_key = Column(Text)
    reality_public_key = Column(Text)
    reality_short_id = Column(String(16))

    vless_inbound_id = Column(Integer, default=1)
    trojan_inbound_id = Column(Integer)
    ss_inbound_id = Column(Integer)

    target_countries = Column(JSONB, default=list)
    excluded_countries = Column(JSONB, default=list)

    last_backup = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
