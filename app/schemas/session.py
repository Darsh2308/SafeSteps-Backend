from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class EmergencySessionStartResponse(BaseModel):
    session_id: str
    tracking_id: str
    created_at: datetime

    model_config = {
        "populate_by_name": True
    }

class LocationUpdate(BaseModel):
    latitude: float
    longitude: float
    accuracy: Optional[float] = 0.0
    speed: Optional[float] = 0.0
    heading: Optional[float] = 0.0

class LocationResponse(BaseModel):
    latitude: float
    longitude: float
    timestamp: datetime
    accuracy: float
    speed: float
    heading: float
    maps_link: Optional[str] = None

    model_config = {
        "from_attributes": True
    }

class TimelineEventSchema(BaseModel):
    time: str = Field(..., description="Formatted string of timestamp")
    event: str

    model_config = {
        "from_attributes": True
    }

class TimelineEventCreate(BaseModel):
    event: str

class TranscriptEventSchema(BaseModel):
    time: str = Field(..., description="Formatted string of timestamp")
    speaker: str  # "User", "System", "Emergency Dispatch", "Emergency Agent"
    text: str
    language: Optional[str] = "English"
    confidence: Optional[float] = 1.0

    model_config = {
        "from_attributes": True
    }

class TranscriptEventCreate(BaseModel):
    speaker: str
    text: str
    language: Optional[str] = "English"
    confidence: Optional[float] = 1.0

class LoggedIncidentSchema(BaseModel):
    id: str
    date: str
    startTime: str = Field(..., alias="startTime")
    endTime: str = Field(..., alias="endTime")
    duration: str
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    incidentType: str = Field(..., alias="incidentType")
    summary: str
    actionsPerformed: List[str] = Field(..., alias="actionsPerformed")
    timeline: List[TimelineEventSchema]
    transcript: List[TranscriptEventSchema]

    model_config = {
        "populate_by_name": True,
        "from_attributes": True
    }

class AnalyticsSchema(BaseModel):
    totalEncounters: int = Field(..., alias="totalEncounters")
    avgResponseLimit: str = Field(..., alias="avgResponseLimit")
    criticalCount: int = Field(..., alias="criticalCount")
    highCount: int = Field(..., alias="highCount")
    mediumCount: int = Field(..., alias="mediumCount")
    lowCount: int = Field(..., alias="lowCount")

    model_config = {
        "populate_by_name": True,
        "from_attributes": True
    }

class CallStatusUpdate(BaseModel):
    state: str  # "Initiated", "Ringing", "Answered", "Ended", "Failed"

class ConversationMessage(BaseModel):
    message: str
    language: Optional[str] = None  # e.g. "hi-IN", "mr-IN", "en-IN"; auto-detected if omitted

class ConversationResponse(BaseModel):
    guidance: str
    questions: List[str]
    recommendations: List[str]

class ReportResponse(BaseModel):
    threatLevel: str = Field(..., alias="threatLevel")
    incidentType: str = Field(..., alias="incidentType")
    summary: str
    actionsTaken: List[str] = Field(..., alias="actionsTaken")
    recommendations: List[str] = Field(..., alias="recommendations")

    model_config = {
        "populate_by_name": True,
        "from_attributes": True
    }

class NotificationRegister(BaseModel):
    deviceToken: str = Field(..., alias="deviceToken")
    deviceType: str = Field(default="ios", alias="deviceType")

class NotificationSendRequest(BaseModel):
    title: str
    body: str

class NotificationResponse(BaseModel):
    id: int
    title: str
    body: str
    sent_at: datetime
    status: str

    model_config = {
        "from_attributes": True
    }
