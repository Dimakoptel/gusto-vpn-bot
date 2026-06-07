"""GUSTO Plan Model"""
from sqlalchemy import Column, Integer, String, Numeric, Text, JSONB, Boolean
from app.database import Base


class GustoPlan(Base):
    __tablename__ = "gusto_plans"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    display_name = Column(String(255))

    price = Column(Numeric(10, 2), nullable=False)
    discount_price = Column(Numeric(10, 2))

    duration_days = Column(Integer, default=30)
    traffic_gb = Column(Numeric(10, 2), default=100)
    device_limit = Column(Integer, default=3)

    features = Column(JSONB, default=list)
    is_popular = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
