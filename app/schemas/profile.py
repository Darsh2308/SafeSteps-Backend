from pydantic import BaseModel, Field
from typing import Optional

class ProfileSchema(BaseModel):
    fullName: str = Field(default="", alias="fullName")
    age: str = Field(default="")
    dateOfBirth: str = Field(default="", alias="dateOfBirth")
    gender: str = Field(default="")
    bloodGroup: str = Field(default="", alias="bloodGroup")
    medicalNotes: str = Field(default="", alias="medicalNotes")
    phone: str = Field(default="")
    preferredLanguage: str = Field(default="English", alias="preferredLanguage")
    notificationEnabled: bool = Field(default=True, alias="notificationEnabled")
    privacyEnabled: bool = Field(default=True, alias="privacyEnabled")
    themeDarkMode: bool = Field(default=True, alias="themeDarkMode")
    sosSensitivity: float = Field(default=0.5, alias="sosSensitivity")

    # This allows Pydantic to read ORM models automatically and translate snake_case/camelCase
    model_config = {
        "populate_by_name": True,
        "from_attributes": True
    }

class ProfileUpdate(BaseModel):
    fullName: Optional[str] = None
    age: Optional[str] = None
    dateOfBirth: Optional[str] = None
    gender: Optional[str] = None
    bloodGroup: Optional[str] = None
    medicalNotes: Optional[str] = None
    preferredLanguage: Optional[str] = None
    notificationEnabled: Optional[bool] = None
    privacyEnabled: Optional[bool] = None
    themeDarkMode: Optional[bool] = None
    sosSensitivity: Optional[float] = None

    model_config = {
        "populate_by_name": True,
        "from_attributes": True
    }

class LanguageUpdate(BaseModel):
    language: str

class SimUpdate(BaseModel):
    simId: int
    name: Optional[str] = ""
    carrier: Optional[str] = ""
    number: Optional[str] = ""

class SettingsSchema(BaseModel):
    notificationEnabled: bool = True
    privacyEnabled: bool = True
    themeDarkMode: bool = True
    sosSensitivity: float = 0.5

    model_config = {
        "populate_by_name": True,
        "from_attributes": True
    }
