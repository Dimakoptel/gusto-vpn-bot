"""Dynamic Application Configuration Model"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.database import Base

class AppConfig(Base):
    __tablename__ = "app_configs"

    id = Column(Integer, primary_key=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    value_type = Column(String(20), default="str")  # str, int, float, bool, json, list
    description = Column(Text)
    category = Column(String(50), default="general")  # brand, payments, telegram, security, router, backup, notifications
    is_sensitive = Column(Boolean, default=False)  # mask in UI (tokens, passwords)
    is_editable = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AppConfig(key={self.key}, category={self.category})>"
