from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.models.user import User
from app.models.notification import Notification
from app.schemas.session import NotificationRegister, NotificationSendRequest, NotificationResponse
from app.services.auth_service import get_current_user
from app.services.notification import notification_service
from app.utils.logger import Logger

router = APIRouter(prefix="/notifications", tags=["Notification System"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_device(payload: NotificationRegister, current_user: User = Depends(get_current_user)):
    from app.models.user import UserDevice
    # Check if already registered
    existing = next(
        (d for d in current_user.devices if d.device_token == payload.deviceToken), None
    )
    if existing:
        existing.is_active = True
        await current_user.save()
        return {"success": True, "message": "Device token updated"}

    current_user.devices.append(UserDevice(
        device_token=payload.deviceToken,
        device_type=payload.deviceType,
        is_active=True,
    ))
    await current_user.save()
    Logger.info(f"Notifications: Registered {payload.deviceType} token for user {current_user.id}")
    return {"success": True, "message": "Device registered"}


@router.post("/send")
async def send_notification(payload: NotificationSendRequest, current_user: User = Depends(get_current_user)):
    success = await notification_service.send_push_notification(
        user_id=current_user.id, title=payload.title, body=payload.body,
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send notification")
    return {"success": True}


@router.get("", response_model=List[NotificationResponse])
async def get_notification_history(current_user: User = Depends(get_current_user)):
    history = await Notification.find(
        Notification.user_id == current_user.id
    ).sort(-Notification.sent_at).to_list()
    return [
        NotificationResponse(id=str(n.id), title=n.title, body=n.body,
                              sent_at=n.sent_at, status=n.status)
        for n in history
    ]
