from fastapi import APIRouter, Depends
from app.models.user import User
from app.schemas.permissions import PermissionSyncRequest, PermissionInfoSchema
from app.services.auth_service import get_current_user
from app.utils.logger import Logger

router = APIRouter(prefix="/permissions", tags=["Permissions Status"])

_cache: dict[str, list] = {}

_DEFAULTS = [
    PermissionInfoSchema(name="Location Access", description="GPS coordinates during emergency.", type="location", status=False),
    PermissionInfoSchema(name="Send SMS", description="Auto-generated alert texts to contacts.", type="sms", status=False),
    PermissionInfoSchema(name="Phone Calls", description="Dial primary contacts or emergency dispatch.", type="phone", status=False),
    PermissionInfoSchema(name="Access Contacts", description="Import trusted contacts from device book.", type="contacts", status=False),
    PermissionInfoSchema(name="Microphone Usage", description="Background audio alerts and transcription.", type="microphone", status=False),
    PermissionInfoSchema(name="Notifications", description="Critical alert statuses and background updates.", type="notifications", status=False),
    PermissionInfoSchema(name="Accessibility Service", description="Hardware trigger intercepts.", type="accessibility", status=False),
]


@router.post("/sync")
async def sync_permissions(payload: PermissionSyncRequest, current_user: User = Depends(get_current_user)):
    _cache[current_user.id] = payload.permissions
    Logger.info(f"Permissions: synced {len(payload.permissions)} for user {current_user.id}")
    return {"success": True, "message": "Permissions synced"}


@router.get("", response_model=PermissionSyncRequest)
async def get_permissions(current_user: User = Depends(get_current_user)):
    return PermissionSyncRequest(permissions=_cache.get(current_user.id, _DEFAULTS))
