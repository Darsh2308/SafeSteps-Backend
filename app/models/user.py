import uuid
from typing import Annotated
from datetime import datetime
from beanie import Document, Indexed
from pydantic import BaseModel, Field


def gen_uuid() -> str:
    return str(uuid.uuid4())


class UserSettings(BaseModel):
    notification_enabled: bool = True
    privacy_enabled: bool = True
    theme_dark_mode: bool = True
    sos_sensitivity: float = 0.5


class UserDevice(BaseModel):
    device_token: str
    device_type: str = "android"
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class User(Document):
    id: str = Field(default_factory=gen_uuid)
    phone: Annotated[str, Indexed(unique=True)]
    full_name: str = ""
    age: str = ""
    date_of_birth: str = ""
    gender: str = ""
    blood_group: str = ""
    medical_notes: str = ""
    preferred_language: str = "English"
    settings: UserSettings = Field(default_factory=UserSettings)
    devices: list[UserDevice] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
