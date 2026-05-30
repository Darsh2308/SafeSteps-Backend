from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.models.user import User
from app.models.session import EmergencySession, TimelineEvent
from app.schemas.session import TimelineEventCreate, TimelineEventSchema
from app.services.auth_service import get_current_user
from app.utils.logger import Logger

router = APIRouter(prefix="/timeline", tags=["Timeline Engine"])


@router.post("/event", response_model=TimelineEventSchema, status_code=status.HTTP_201_CREATED)
async def create_timeline_event(payload: TimelineEventCreate, current_user: User = Depends(get_current_user)):
    session = await EmergencySession.find_one(
        EmergencySession.user_id == current_user.id,
        EmergencySession.status == "active",
    )
    if not session:
        session = await EmergencySession.find_one(
            EmergencySession.user_id == current_user.id
        ).sort(-EmergencySession.created_at)
        if not session:
            raise HTTPException(status_code=404, detail="No session found")

    evt = TimelineEvent(event=payload.event)
    session.timeline.append(evt)
    await session.save()
    Logger.info(f"Timeline: '{payload.event}' for session {session.id}")
    return TimelineEventSchema(time=evt.timestamp.strftime("%H:%M:%S"), event=evt.event)


@router.get("/{session_id}", response_model=List[TimelineEventSchema])
async def get_timeline(session_id: str, current_user: User = Depends(get_current_user)):
    session = await EmergencySession.find_one(
        EmergencySession.id == session_id,
        EmergencySession.user_id == current_user.id,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return [TimelineEventSchema(time=e.timestamp.strftime("%H:%M:%S"), event=e.event) for e in session.timeline]
