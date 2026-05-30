from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.models.user import User
from app.models.session import EmergencySession, SessionTranscript
from app.schemas.session import TranscriptEventCreate, TranscriptEventSchema
from app.services.auth_service import get_current_user
from app.utils.logger import Logger

router = APIRouter(prefix="/transcript", tags=["Transcript Management"])


@router.post("", response_model=TranscriptEventSchema, status_code=status.HTTP_201_CREATED)
async def create_transcript(payload: TranscriptEventCreate, current_user: User = Depends(get_current_user)):
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

    t = SessionTranscript(
        speaker=payload.speaker, text=payload.text,
        language=payload.language or "en-IN",
        confidence=payload.confidence or 1.0,
    )
    session.transcripts.append(t)
    await session.save()
    Logger.info(f"Transcript: '{payload.text[:30]}…' from {payload.speaker}")
    return TranscriptEventSchema(
        time=t.timestamp.strftime("%H:%M:%S"), speaker=t.speaker,
        text=t.text, language=t.language, confidence=t.confidence,
    )


@router.get("/{session_id}", response_model=List[TranscriptEventSchema])
async def get_transcript(session_id: str, current_user: User = Depends(get_current_user)):
    session = await EmergencySession.find_one(
        EmergencySession.id == session_id,
        EmergencySession.user_id == current_user.id,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return [
        TranscriptEventSchema(
            time=t.timestamp.strftime("%H:%M:%S"), speaker=t.speaker,
            text=t.text, language=t.language, confidence=t.confidence,
        ) for t in session.transcripts
    ]
