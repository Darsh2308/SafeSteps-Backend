from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.models.user import User
from app.services.auth_service import get_current_user
from app.services.tts_service import tts_service
from app.utils.logger import Logger

router = APIRouter(prefix="/tts", tags=["Text To Speech"])


class TTSRequest(BaseModel):
    text: str
    language: str = "en-IN"


@router.post("/synthesize")
async def synthesize_speech(
    payload: TTSRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Convert AI guidance text to speech using Sarvam Bulbul TTS.

    Returns WAV audio bytes when online. Returns 204 No Content when Sarvam API
    key is unavailable — mobile app then falls back to Android Native TTS.

    Languages: en-IN, hi-IN, mr-IN (and other supported Sarvam codes)
    """
    if not payload.text or not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text is required")

    Logger.info(f"TTS Router: Synthesizing {len(payload.text)} chars in {payload.language} for user {current_user.id}")

    audio_bytes = await tts_service.synthesize(payload.text, payload.language)

    if audio_bytes is None:
        # No API key or synthesis failed — mobile uses Android Native TTS
        return Response(status_code=204)

    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers={"Content-Disposition": "inline; filename=response.wav"},
    )
