from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.models.user import User
from app.models.session import EmergencySession, SessionLocation, TimelineEvent
from app.schemas.session import LocationUpdate, LocationResponse
from app.services.auth_service import get_current_user
from app.utils.logger import Logger

router = APIRouter(prefix="/location", tags=["Live Location Tracking"])


def build_maps_link(lat: float, lon: float) -> str:
    return f"https://maps.google.com/?q={lat},{lon}"


@router.post("/update")
async def update_location(
    payload: LocationUpdate,
    current_user: User = Depends(get_current_user),
):
    session = await EmergencySession.find_one(
        EmergencySession.user_id == current_user.id,
        EmergencySession.status == "active",
    )
    if not session:
        raise HTTPException(status_code=404, detail="No active emergency session found")

    maps_link = build_maps_link(payload.latitude, payload.longitude)
    is_first = len(session.locations) == 0

    loc = SessionLocation(
        latitude=payload.latitude, longitude=payload.longitude,
        accuracy=payload.accuracy or 0.0, speed=payload.speed or 0.0,
        heading=payload.heading or 0.0,
    )
    session.locations.append(loc)

    if is_first:
        session.timeline.append(TimelineEvent(event="GPS Coordinates Acquired"))

    await session.save()

    Logger.debug(f"Location: lat={payload.latitude}, lon={payload.longitude} → session {session.id}")
    # maps_link returned to app — app sends SOS SMS via Android SmsManager using user's SIM
    return {"success": True, "maps_link": maps_link, "is_first_update": is_first}


@router.get("/{session_id}", response_model=LocationResponse)
async def get_latest_location(session_id: str, current_user: User = Depends(get_current_user)):
    session = await EmergencySession.find_one(
        EmergencySession.id == session_id,
        EmergencySession.user_id == current_user.id,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.locations:
        raise HTTPException(status_code=404, detail="No location data yet")
    last = session.locations[-1]
    return LocationResponse(
        latitude=last.latitude, longitude=last.longitude, timestamp=last.timestamp,
        accuracy=last.accuracy, speed=last.speed, heading=last.heading,
        maps_link=build_maps_link(last.latitude, last.longitude),
    )


@router.get("/history/{session_id}", response_model=List[LocationResponse])
async def get_location_history(session_id: str, current_user: User = Depends(get_current_user)):
    session = await EmergencySession.find_one(
        EmergencySession.id == session_id,
        EmergencySession.user_id == current_user.id,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return [
        LocationResponse(
            latitude=l.latitude, longitude=l.longitude, timestamp=l.timestamp,
            accuracy=l.accuracy, speed=l.speed, heading=l.heading,
            maps_link=build_maps_link(l.latitude, l.longitude),
        ) for l in session.locations
    ]
