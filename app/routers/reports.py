from fastapi import APIRouter, Depends, HTTPException
from app.models.user import User
from app.models.session import EmergencySession
from app.schemas.session import ReportResponse
from app.services.auth_service import get_current_user
from app.services.report_service import report_service

router = APIRouter(prefix="/report", tags=["Emergency Reporting"])


def _resp(session: EmergencySession) -> ReportResponse:
    r = session.report
    if not r:
        return ReportResponse(threatLevel="LOW", incidentType="SOS Incident",
                              summary="", actionsTaken=[], recommendations=[])
    return ReportResponse(
        threatLevel=r.threat_level, incidentType=r.incident_type,
        summary=r.summary, actionsTaken=r.actions_taken,
        recommendations=r.recommendations,
    )


@router.post("/generate", response_model=ReportResponse)
async def generate_report(session_id: str, current_user: User = Depends(get_current_user)):
    session = await EmergencySession.find_one(
        EmergencySession.id == session_id,
        EmergencySession.user_id == current_user.id,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await report_service.generate_and_save_report(session)
    await session.save()
    return _resp(session)


@router.get("/{session_id}", response_model=ReportResponse)
async def get_report(session_id: str, current_user: User = Depends(get_current_user)):
    session = await EmergencySession.find_one(
        EmergencySession.id == session_id,
        EmergencySession.user_id == current_user.id,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.report:
        await report_service.generate_and_save_report(session)
        await session.save()
    return _resp(session)
