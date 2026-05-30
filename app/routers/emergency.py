from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import datetime

from app.models.user import User
from app.models.session import EmergencySession, TimelineEvent, ThreatAssessment
from app.schemas.session import EmergencySessionStartResponse, LoggedIncidentSchema, TimelineEventSchema, TranscriptEventSchema
from app.services.auth_service import get_current_user
from app.services.report_service import report_service
from app.utils.logger import Logger

router = APIRouter(prefix="/emergency", tags=["Emergency Sessions"])


def _format_duration(start: datetime, end: Optional[datetime]) -> str:
    if not end:
        return "Active"
    delta = end - start
    m, s = divmod(int(delta.total_seconds()), 60)
    return f"{m}m {s}s" if m else f"{s}s"


def _compile(session: EmergencySession) -> LoggedIncidentSchema:
    timeline = [TimelineEventSchema(time=e.timestamp.strftime("%H:%M:%S"), event=e.event) for e in session.timeline]
    transcripts = [
        TranscriptEventSchema(
            time=t.timestamp.strftime("%H:%M:%S"), speaker=t.speaker,
            text=t.text, language=t.language, confidence=t.confidence,
        ) for t in session.transcripts
    ]
    severity = "LOW"
    incident_type = "SOS Activation"
    summary = "Emergency session activated."
    actions: List[str] = ["SOS Activated"]

    if session.report:
        r = session.report
        severity = r.threat_level
        incident_type = r.incident_type
        summary = r.summary
        actions = r.actions_taken
    elif session.threat_assessments:
        last = session.threat_assessments[-1]
        severity = last.threat_level
        summary = last.reasons

    return LoggedIncidentSchema(
        id=session.id,
        date=session.created_at.strftime("%Y-%m-%d"),
        startTime=session.created_at.strftime("%H:%M:%S"),
        endTime=session.ended_at.strftime("%H:%M:%S") if session.ended_at else "Active",
        duration=_format_duration(session.created_at, session.ended_at),
        severity=severity,
        incidentType=incident_type,
        summary=summary,
        actionsPerformed=actions,
        timeline=timeline,
        transcript=transcripts,
    )


@router.post("/start", response_model=EmergencySessionStartResponse)
async def start_session(current_user: User = Depends(get_current_user)):
    # Close any existing active session first
    active = await EmergencySession.find_one(
        EmergencySession.user_id == current_user.id,
        EmergencySession.status == "active",
    )
    if active:
        active.status = "ended"
        active.ended_at = datetime.utcnow()
        await active.save()

    session = EmergencySession(
        user_id=current_user.id,
        timeline=[TimelineEvent(event="SOS Activated")],
        threat_assessments=[ThreatAssessment(
            threat_level="LOW", confidence=1.0,
            reasons="Emergency session started by user.",
        )],
    )
    await session.insert()
    Logger.info(f"Emergency: SOS started — session {session.id} for user {current_user.id}")
    return EmergencySessionStartResponse(
        session_id=session.id, tracking_id=session.tracking_id, created_at=session.created_at,
    )


@router.post("/end", response_model=LoggedIncidentSchema)
async def end_session(current_user: User = Depends(get_current_user)):
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
    else:
        session.status = "ended"
        session.ended_at = datetime.utcnow()
        session.timeline.append(TimelineEvent(event="SOS Deactivated — User Marked Safe"))
        await session.save()

        # Safe SMS is sent by the app via Android SmsManager using the user's SIM
        try:
            await report_service.generate_and_save_report(session)
            await session.save()
        except Exception as e:
            Logger.error(f"Report generation failed: {e}")

    return _compile(session)


@router.get("/current", response_model=Optional[EmergencySessionStartResponse])
async def get_current_session(current_user: User = Depends(get_current_user)):
    session = await EmergencySession.find_one(
        EmergencySession.user_id == current_user.id,
        EmergencySession.status == "active",
    )
    if not session:
        return None
    return EmergencySessionStartResponse(
        session_id=session.id, tracking_id=session.tracking_id, created_at=session.created_at,
    )


@router.get("/incidents", response_model=List[LoggedIncidentSchema])
async def get_incidents(current_user: User = Depends(get_current_user)):
    sessions = await EmergencySession.find(
        EmergencySession.user_id == current_user.id
    ).sort(-EmergencySession.created_at).to_list()
    return [_compile(s) for s in sessions]


@router.get("/history", response_model=List[LoggedIncidentSchema])
async def get_history(current_user: User = Depends(get_current_user)):
    return await get_incidents(current_user)


@router.post("/trigger", response_model=LoggedIncidentSchema)
async def trigger_sos(current_user: User = Depends(get_current_user)):
    resp = await start_session(current_user)
    session = await EmergencySession.find_one(EmergencySession.id == resp.session_id)
    return _compile(session)


@router.get("/{session_id}", response_model=LoggedIncidentSchema)
async def get_session_by_id(session_id: str, current_user: User = Depends(get_current_user)):
    session = await EmergencySession.find_one(
        EmergencySession.id == session_id,
        EmergencySession.user_id == current_user.id,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return _compile(session)
