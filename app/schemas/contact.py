from pydantic import BaseModel, Field
from typing import Optional

class ContactCreate(BaseModel):
    name: str
    relationship: str
    phoneNumber: str = Field(..., alias="phoneNumber")
    priority: str = "Primary"  # "Primary", "Secondary", "Tertiary"

    model_config = {
        "populate_by_name": True,
        "from_attributes": True
    }

class ContactSchema(BaseModel):
    id: str
    name: str
    relationship: str
    phoneNumber: str = Field(..., alias="phoneNumber")
    priority: str

    model_config = {
        "populate_by_name": True,
        "from_attributes": True
    }
