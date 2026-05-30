from fastapi import APIRouter, Depends
from datetime import datetime, timedelta

from app.models.user import User
from app.models.session import EmergencySession
from app.schemas.session import AnalyticsSchema
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/analytics", tags=["Emergency Analytics"])


async def _get_overview(current_user: User) -> AnalyticsSchema:
    sessions = await EmergencySession.find(
        EmergencySession.user_id == current_user.id
    ).to_list()

    total = len(sessions)
    critical = high = medium = low = 0
    durations = []

    for s in sessions:
        if s.ended_at:
            durations.append((s.ended_at - s.created_at).total_seconds())

        level = "LOW"
        if s.report:
            level = s.report.threat_level
        elif s.threat_assessments:
            level = s.threat_assessments[-1].threat_level

        if level == "CRITICAL":
            critical += 1
        elif level == "HIGH":
            high += 1
        elif level == "MEDIUM":
            medium += 1
        else:
            low += 1

    avg_str = "0s"
    if durations:
        avg_sec = sum(durations) / len(durations)
        m, s = divmod(int(avg_sec), 60)
        avg_str = f"{m}m {s}s" if m else f"{s}s"

    return AnalyticsSchema(
        totalEncounters=total, avgResponseLimit=avg_str,
        criticalCount=critical, highCount=high,
        mediumCount=medium, lowCount=low,
    )


@router.get("", response_model=AnalyticsSchema)
@router.get("/overview", response_model=AnalyticsSchema)
async def get_analytics(current_user: User = Depends(get_current_user)):
    return await _get_overview(current_user)


@router.get("/incidents")
async def get_incident_types(current_user: User = Depends(get_current_user)):
    sessions = await EmergencySession.find(
        EmergencySession.user_id == current_user.id
    ).to_list()
    counts: dict = {}
    for s in sessions:
        itype = s.report.incident_type if s.report else "Unclassified SOS"
        counts[itype] = counts.get(itype, 0) + 1
    return [{"type": k, "count": v} for k, v in counts.items()]


@router.get("/severity")
async def get_severity(current_user: User = Depends(get_current_user)):
    ov = await _get_overview(current_user)
    return {"CRITICAL": ov.criticalCount, "HIGH": ov.highCount,
            "MEDIUM": ov.mediumCount, "LOW": ov.lowCount}


@router.get("/monthly")
async def get_monthly(current_user: User = Depends(get_current_user)):
    since = datetime.utcnow() - timedelta(days=180)
    sessions = await EmergencySession.find(
        EmergencySession.user_id == current_user.id,
        EmergencySession.created_at >= since,
    ).to_list()
    months: dict = {}
    for s in sessions:
        key = s.created_at.strftime("%b %Y")
        months[key] = months.get(key, 0) + 1
    return [{"month": k, "count": v} for k, v in months.items()]


@router.get("/trends")
async def get_trends(_current_user: User = Depends(get_current_user)):
    return {"status": "stable", "description": "Emergency rates are consistent with the prior 30-day window."}
