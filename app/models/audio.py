from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class SessionTranscript(Base):
    __tablename__ = "session_transcripts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("emergency_sessions.id", ondelete="CASCADE"), nullable=False)
    speaker = Column(String(50), nullable=False)  # "User", "System", "Emergency Dispatch", "Emergency Agent"
    text = Column(String(1000), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    language = Column(String(20), default="English")
    confidence = Column(Float, default=1.0)

    session = relationship("EmergencySession", back_populates="transcripts")

class AudioEvent(Base):
    __tablename__ = "audio_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("emergency_sessions.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(100), nullable=False)  # "Screams", "Crying", "Aggression", "Vehicle Crash", "Glass Breaking", "Heavy Breathing"
    confidence = Column(Float, default=1.0)
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("EmergencySession", back_populates="audio_events")
