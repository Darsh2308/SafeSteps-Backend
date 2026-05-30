from sqlalchemy import Column, String, Integer, DateTime, Text
from datetime import datetime
from app.database import Base

class AnalyticsCache(Base):
    __tablename__ = "analytics_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_key = Column(String(100), unique=True, index=True, nullable=False)
    metric_value = Column(Text, nullable=False)  # JSON encoded metric
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
