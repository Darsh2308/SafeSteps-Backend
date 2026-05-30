from pydantic import BaseModel, Field
from typing import Optional
from app.schemas.profile import ProfileSchema


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
