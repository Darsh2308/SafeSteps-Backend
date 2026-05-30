import uuid
from typing import Optional
from datetime import datetime
from beanie import Document
from pydantic import BaseModel, Field


def gen_uuid() -> str:
    return str(uuid.uuid4())


# ── Embedded sub-documents (not separate collections) ─────────────────────────

class SessionLocation(BaseModel):
    latitude: float
    longitude: float
    accuracy: float = 0.0
    speed: float = 0.0
    heading: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TimelineEvent(BaseModel):
    event: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CallLog(BaseModel):
    state: str  # "Initiated" | "Ringing" | "Answered" | "Ended" | "Failed"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SessionTranscript(BaseModel):
    speaker: str  # "User" | "Emergency Agent"
    text: str
    language: str = "en-IN"
    confidence: float = 1.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AudioEvent(BaseModel):
    event_type: str  # "Screams" | "Crying" | "Aggression" | "Vehicle Crash" | ...
    confidence: float = 1.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ThreatAssessment(BaseModel):
    threat_level: str  # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    confidence: float = 1.0
    reasons: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SessionReport(BaseModel):
    threat_level: str = "LOW"
    incident_type: str = "SOS Incident"
    summary: str = ""
    actions_taken: list[str] = []
    recommendations: list[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── Main session document (all sub-data embedded) ─────────────────────────────

class EmergencySession(Document):
    id: str = Field(default_factory=gen_uuid)
    user_id: str
    tracking_id: str = Field(default_factory=gen_uuid)
    status: str = "active"  # "active" | "ended"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None

    locations: list[SessionLocation] = []
    timeline: list[TimelineEvent] = []
    call_logs: list[CallLog] = []
    transcripts: list[SessionTranscript] = []
    audio_events: list[AudioEvent] = []
    threat_assessments: list[ThreatAssessment] = []
    report: Optional[SessionReport] = None

    class Settings:
        name = "emergency_sessions"
