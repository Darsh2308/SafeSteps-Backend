from fastapi import APIRouter, Depends

from app.models.user import User
from app.models.session import EmergencySession, SessionTranscript
from app.schemas.session import ConversationMessage, ConversationResponse
from app.services.auth_service import get_current_user
from app.services.ai_service import ai_service
from app.utils.logger import Logger

router = APIRouter(prefix="/conversation", tags=["AI Conversation Module"])


@router.post("/message", response_model=ConversationResponse)
async def handle_message(
    payload: ConversationMessage,
    current_user: User = Depends(get_current_user),
):
    session = await EmergencySession.find_one(
        EmergencySession.user_id == current_user.id,
        EmergencySession.status == "active",
    )

    threat_level = "LOW"
    language = payload.language or "en-IN"

    if session:
        if session.threat_assessments:
            threat_level = session.threat_assessments[-1].threat_level
        if not payload.language and session.transcripts:
            last_user_t = next(
                (t for t in reversed(session.transcripts) if t.speaker == "User"), None
            )
            if last_user_t and last_user_t.language:
                language = last_user_t.language

    Logger.info(f"Conversation: lang={language} threat={threat_level} user={current_user.id}")

    # Build history from last 5 exchanges
    history = []
    if session and session.transcripts:
        for t in session.transcripts[-10:]:
            role = "user" if t.speaker == "User" else "assistant"
            history.append({"role": role, "content": t.text})

    ai_resp = await ai_service.generate_safety_response(
        message=payload.message,
        threat_level=threat_level,
        history=history,
        language=language,
    )

    if session:
        session.transcripts.append(SessionTranscript(
            speaker="User", text=payload.message, language=language,
        ))
        session.transcripts.append(SessionTranscript(
            speaker="Emergency Agent", text=ai_resp.get("guidance", ""),
            language=language,
        ))
        await session.save()

    return ConversationResponse(
        guidance=ai_resp.get("guidance", ""),
        questions=ai_resp.get("questions", []),
        recommendations=ai_resp.get("recommendations", []),
    )
