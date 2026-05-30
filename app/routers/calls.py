from fastapi import APIRouter, Depends, HTTPException
from app.models.user import User
from app.models.session import EmergencySession, CallLog, TimelineEvent
from app.schemas.session import CallStatusUpdate
from app.services.auth_service import get_current_user
from app.utils.logger import Logger

router = APIRouter(prefix="/call", tags=["Call Status Tracking"])


@router.post("/status")
async def update_call_status(payload: CallStatusUpdate, current_user: User = Depends(get_current_user)):
    session = await EmergencySession.find_one(
        EmergencySession.user_id == current_user.id,
        EmergencySession.status == "active",
    )
    if not session:
        session = await EmergencySession.find_one(
            EmergencySession.user_id == current_user.id
        ).sort(-EmergencySession.created_at)
        if not session:
            raise HTTPException(status_code=404, detail="No emergency session found")

    session.call_logs.append(CallLog(state=payload.state))
    session.timeline.append(TimelineEvent(event=f"Call Status → {payload.state}"))
    await session.save()
    Logger.info(f"Call: status='{payload.state}' for session {session.id}")
    return {"success": True, "message": "Call status updated"}


@router.get("/{session_id}")
async def get_call_status(session_id: str, current_user: User = Depends(get_current_user)):
    session = await EmergencySession.find_one(
        EmergencySession.id == session_id,
        EmergencySession.user_id == current_user.id,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.call_logs:
        return {"state": "None", "history": []}
    return {
        "state": session.call_logs[-1].state,
        "history": [{"state": c.state, "timestamp": c.timestamp.isoformat()} for c in session.call_logs],
    }
