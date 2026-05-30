from pydantic import BaseModel
from typing import List

class PermissionInfoSchema(BaseModel):
    name: str
    description: str
    type: str  # e.g., 'location', 'sms', etc.
    status: bool

    model_config = {
        "from_attributes": True
    }

class PermissionSyncRequest(BaseModel):
    permissions: List[PermissionInfoSchema]
