import uuid
from datetime import datetime
from beanie import Document
from pydantic import Field


def gen_uuid() -> str:
    return str(uuid.uuid4())


class EmergencyContact(Document):
    id: str = Field(default_factory=gen_uuid)
    user_id: str
    name: str
    relationship: str
    phone_number: str
    priority: str = "Primary"  # "Primary", "Secondary", "Tertiary"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "emergency_contacts"
