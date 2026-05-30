import asyncio
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime

from app.models.session import (
    EmergencySession, SessionTranscript, AudioEvent as AudioEventModel,
    ThreatAssessment, TimelineEvent,
)
from app.services.vad_service import vad_service
from app.services.stt_service import stt_service
from app.services.ai_threat_service import ai_threat_service
from app.services.notification import notification_service
from app.utils.logger import Logger

router = APIRouter(tags=["Live Audio Streaming"])


class ConnectionManager:
    def __init__(self):
        self._conns: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, ws: WebSocket):
        await ws.accept()
        self._conns[session_id] = ws
        Logger.info(f"WS: session {session_id} connected")

    def disconnect(self, session_id: str):
        self._conns.pop(session_id, None)
        Logger.info(f"WS: session {session_id} disconnected")

    async def send_json(self, session_id: str, msg: dict):
        ws = self._conns.get(session_id)
        if ws:
            try:
                await ws.send_json(msg)
            except Exception as e:
                Logger.error(f"WS send error for {session_id}: {e}")


manager = ConnectionManager()


@router.websocket("/ws/audio/{session_id}")
async def websocket_audio_endpoint(websocket: WebSocket, session_id: str):
    # Verify session exists (creates dummy if missing, for test resilience)
    session = await EmergencySession.find_one(EmergencySession.id == session_id)
    if not session:
        Logger.warn(f"WS: session {session_id} not found — creating dummy")
        session = EmergencySession(id=session_id, user_id="ws_test_user")
        await session.insert()

    await manager.connect(session_id, websocket)

    audio_buffer = bytearray()
    speech_buffer = bytearray()
    silence_counter = 0
    speech_counter = 0
    CHUNK_SIZE = 16000  # 0.5 s of 16kHz 16-bit mono PCM
    session_state = {"prior_threat": "LOW", "last_stt_time": 0.0}

    try:
        while True:
            data = await websocket.receive_bytes()
            audio_buffer.extend(data)

            while len(audio_buffer) >= CHUNK_SIZE:
                chunk = bytes(audio_buffer[:CHUNK_SIZE])
                del audio_buffer[:CHUNK_SIZE]

                if vad_service.is_speech(chunk):
                    speech_buffer.extend(chunk)
                    speech_counter += 1
                    silence_counter = 0
                else:
                    silence_counter += 1
                    if speech_buffer:
                        speech_buffer.extend(chunk)

                if speech_counter >= 6 or (silence_counter >= 3 and speech_buffer):
                    chunk_to_process = bytes(speech_buffer)
                    speech_buffer = bytearray()
                    speech_counter = 0
                    silence_counter = 0
                    asyncio.create_task(
                        _process_pipeline(session_id, chunk_to_process, session_state)
                    )

    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        Logger.error(f"WS stream error for {session_id}: {e}")
        manager.disconnect(session_id)


async def _process_pipeline(session_id: str, audio_data: bytes, session_state: dict):
    """
    STT → AI Threat Analysis (Groq) → GPS/Call overrides → WS push.
    Each task fetches its own DB session to avoid concurrent-access issues.
    """
    STT_COOLDOWN = 3.0  # min seconds between Sarvam STT calls (avoid 429)

    try:
        # 1. STT cooldown gate
        now = time.monotonic()
        if now - session_state.get("last_stt_time", 0.0) < STT_COOLDOWN:
            return
        session_state["last_stt_time"] = now

        # 2. Speech-to-Text
        stt_result = await asyncio.to_thread(stt_service.transcribe, audio_data)
        transcript = stt_result.get("transcript", "")
        language   = stt_result.get("language", "en-IN")
        confidence = stt_result.get("confidence", 0.9)

        if not transcript.strip():
            return

        # 3. Fetch session
        session = await EmergencySession.find_one(EmergencySession.id == session_id)
        if not session:
            return

        # Save transcript
        session.transcripts.append(SessionTranscript(
            speaker="User", text=transcript, language=language, confidence=confidence,
        ))

        # 4. AI Threat Analysis — Groq understands full context, not just keywords
        recent_texts = [t.text for t in session.transcripts[-4:]]
        prior_threat = session_state["prior_threat"]

        analysis = await ai_threat_service.analyze(
            transcript=transcript,
            language=language,
            prior_threat=prior_threat,
            recent_transcripts=recent_texts,
        )

        threat_level  = analysis["threat_level"]
        events        = analysis["events"]          # list[str] e.g. ["Screams", "Aggression"]
        is_safe       = analysis["is_safe"]
        incident_type = analysis["incident_type"]
        reasons       = analysis["reasons"]

        # 5. Save AI-detected audio events
        for event_type in events:
            session.audio_events.append(AudioEventModel(
                event_type=event_type,
                confidence=0.90,
                timestamp=datetime.utcnow(),
            ))
            session.timeline.append(TimelineEvent(
                event=f"Audio Event: {event_type} (AI-detected)"
            ))

        # 6. GPS speed override — non-text signal, stays rule-based
        speeds    = [loc.speed for loc in session.locations[-5:]]
        max_speed = max(speeds) if speeds else 0.0
        if max_speed > 80.0:
            if "Vehicle Crash" in events and threat_level != "CRITICAL":
                threat_level = "CRITICAL"
                reasons += "; High-speed movement combined with crash event."
            elif threat_level == "LOW":
                threat_level = "MEDIUM"
                reasons += "; High-speed movement detected."

        # 7. Call status override — non-text signal, stays rule-based
        call_states = [c.state for c in session.call_logs[-5:]]
        if "Failed" in call_states and threat_level == "LOW":
            threat_level = "MEDIUM"
            reasons += "; Emergency call failed to connect."

        # 8. Record threat assessment
        session.threat_assessments.append(ThreatAssessment(
            threat_level=threat_level, confidence=0.90, reasons=reasons,
        ))

        # 9. Timeline + push notification on threat change
        if threat_level != prior_threat:
            session_state["prior_threat"] = threat_level
            session.timeline.append(TimelineEvent(event=f"Threat Level → {threat_level}"))

            if threat_level in ["HIGH", "CRITICAL"] and session.user_id != "ws_test_user":
                await notification_service.send_push_notification(
                    user_id=session.user_id,
                    title=f"SOS ALERT: {threat_level} Threat Detected",
                    body=reasons,
                )

        # Reset prior threat to LOW when user confirms safety
        if is_safe:
            session_state["prior_threat"] = "LOW"
            session.timeline.append(TimelineEvent(event="User confirmed safety — session de-escalated."))

        await session.save()

        # 10. Push result to mobile app via WebSocket
        await manager.send_json(session_id, {
            "type":          "threat_update",
            "session_id":    session_id,
            "transcript":    transcript,
            "language":      language,
            "threat_level":  threat_level,
            "events":        events,
            "is_safe":       is_safe,
            "incident_type": incident_type,
            "reasons":       reasons,
            "timestamp":     datetime.utcnow().isoformat(),
        })

    except Exception as e:
        Logger.error(f"WS pipeline error for {session_id}: {e}")
