from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class ThreatAssessment(Base):
    __tablename__ = "threat_assessments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("emergency_sessions.id", ondelete="CASCADE"), nullable=False)
    threat_level = Column(String(20), nullable=False)  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    confidence = Column(Float, default=1.0)
    reasons = Column(Text, default="")
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("EmergencySession", back_populates="threat_assessments")

class SessionReport(Base):
    __tablename__ = "session_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("emergency_sessions.id", ondelete="CASCADE"), nullable=False)
    threat_level = Column(String(20), nullable=False)  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    incident_type = Column(String(100), default="")
    summary = Column(Text, default="")
    actions_taken = Column(Text, default="[]")  # JSON encoded list of actions
    recommendations = Column(Text, default="[]")  # JSON encoded list of recommendations
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("EmergencySession", back_populates="reports")
