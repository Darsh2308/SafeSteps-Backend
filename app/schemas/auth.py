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

    # Allows Pydantic to read ORM models and translate snake_case/camelCase
    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
    }


class RegisterRequest(BaseModel):
    phone: str = Field(..., description="User's phone number (used as unique login ID)")
    full_name: str = Field(..., description="Full name")
    age: Optional[str] = ""
    date_of_birth: Optional[str] = ""
    gender: Optional[str] = ""
    blood_group: Optional[str] = ""
    medical_notes: Optional[str] = ""
    preferred_language: Optional[str] = "English"


class LoginRequest(BaseModel):
    phone: str = Field(..., description="Registered phone number")


class TokenResponse(BaseModel):
    success: bool
    token: str
    user: ProfileSchema
