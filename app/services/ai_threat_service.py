import json
import httpx
from app.config import settings
from app.utils.logger import Logger

_GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODEL = "llama-3.1-8b-instant"

_SYSTEM_PROMPT = """You are SafeSteps AI — a real-time emergency threat analyzer embedded in a personal safety app.

A user has triggered an SOS alert. You receive live speech transcripts from their microphone during an active emergency session.

YOUR JOB:
Analyze the transcript and return a threat assessment. You must understand FULL CONTEXT — not just keywords.

IMPORTANT RULES:
- "I'm killing it at work" = LOW. Context matters. Idioms are not threats.
- "There's someone behind me" = HIGH even without panic words — infer danger from situation.
- "Police is here", "I am safe", "false alarm", "all clear" = is_safe: true, threat: LOW.
- Understand English, Hindi (Devanagari + Roman transliteration), and Marathi naturally.
- Use prior_threat as context — if prior was HIGH, a neutral statement alone should give MEDIUM minimum (unless is_safe is true).
- Distinguish between reporting an event vs experiencing it: "I saw a crash yesterday" ≠ current threat.

THREAT LEVELS:
LOW      — Normal conversation. No threat indicators. User is calm.
MEDIUM   — Mild concern. Suspicious situation. User seems uneasy, something feels off.
HIGH     — Clear threat. Being followed or watched. Someone threatening nearby. Scared, running.
CRITICAL — Immediate physical danger. Active assault, crash in progress, weapon present, screaming, can't breathe.

EVENTS (only include if genuinely detected in THIS transcript):
- Screams          : User is screaming or clearly describes screaming happening right now
- Aggression       : Physical violence, weapon mentioned, someone attacking
- Crying           : User is crying or sobbing from extreme distress
- Vehicle Crash    : Car accident or collision happening or just happened
- Heavy Breathing  : Panic attack, choking, gasping

INCIDENT TYPES:
Stalking, Assault, Robbery, Harassment, Accident, Medical Emergency, Unknown, None

Return ONLY a valid JSON object with exactly these keys:
{
  "threat_level": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
  "events": [],
  "is_safe": false,
  "incident_type": "None",
  "reasons": "one sentence explanation"
}"""


class AIThreatService:
    def __init__(self):
        self._ready = bool(settings.GROQ_API_KEY)
        if self._ready:
            Logger.info("AI Threat Service: Groq-powered threat analysis ready.")
        else:
            Logger.warn("AI Threat Service: GROQ_API_KEY not set — using keyword fallback only.")

    async def analyze(
        self,
        transcript: str,
        language: str = "en-IN",
        prior_threat: str = "LOW",
        recent_transcripts: list = None,
    ) -> dict:
        """
        Analyzes a speech transcript using Groq LLM to determine threat level,
        detected events, and whether the user confirmed safety.

        Falls back to keyword-based detection if Groq is unavailable or fails.

        Returns:
            dict: { threat_level, events[], is_safe, incident_type, reasons }
        """
        if not transcript.strip():
            return _empty_result()

        if self._ready:
            try:
                return await self._call_groq(transcript, language, prior_threat, recent_transcripts or [])
            except Exception as e:
                Logger.error(f"AI Threat: Groq call failed: {e}. Using keyword fallback.")

        return self._keyword_fallback(transcript, prior_threat)

    async def _call_groq(
        self, transcript: str, language: str, prior_threat: str, recent_transcripts: list
    ) -> dict:
        context_block = ""
        if recent_transcripts:
            lines = "\n".join(f"  - {t}" for t in recent_transcripts[-3:])
            context_block = f"\nRecent conversation context (for continuity):\n{lines}\n"

        user_content = (
            f"Language detected: {language}\n"
            f"Prior threat level: {prior_threat}\n"
            f"{context_block}"
            f"Current transcript: \"{transcript}\"\n\n"
            f"Return JSON: threat_level, events (array), is_safe (bool), incident_type, reasons"
        )

        payload = {
            "model": _GROQ_MODEL,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_content},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 256,
        }
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(_GROQ_API_URL, json=payload, headers=headers)
            resp.raise_for_status()

        data = json.loads(resp.json()["choices"][0]["message"]["content"])
        return _sanitize(data)

    def _keyword_fallback(self, transcript: str, prior_threat: str) -> dict:
        from app.services.threat_fusion import threat_fusion_engine
        fusion = threat_fusion_engine.assess_threat(
            transcripts=[transcript],
            audio_events=[],
            speeds=[],
            call_states=[],
            prior_threat=prior_threat,
        )
        return {
            "threat_level": fusion["threat_level"],
            "events": [],
            "is_safe": False,
            "incident_type": "Unknown",
            "reasons": fusion["reasons"] + " [keyword fallback]",
        }


_VALID_THREATS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
_VALID_EVENTS  = {"Screams", "Aggression", "Crying", "Vehicle Crash", "Heavy Breathing"}
_VALID_INCIDENTS = {
    "None", "Stalking", "Assault", "Robbery",
    "Harassment", "Accident", "Medical Emergency", "Unknown",
}


def _sanitize(data: dict) -> dict:
    threat_level = data.get("threat_level", "LOW")
    if threat_level not in _VALID_THREATS:
        threat_level = "LOW"

    events = [e for e in data.get("events", []) if e in _VALID_EVENTS]
    is_safe = bool(data.get("is_safe", False))
    incident_type = data.get("incident_type", "None")
    if incident_type not in _VALID_INCIDENTS:
        incident_type = "Unknown"
    reasons = str(data.get("reasons", ""))[:300]

    Logger.info(
        f"AI Threat: {threat_level} | {incident_type} | events={events} "
        f"| safe={is_safe} | {reasons[:80]}"
    )
    return {
        "threat_level": threat_level,
        "events": events,
        "is_safe": is_safe,
        "incident_type": incident_type,
        "reasons": reasons,
    }


def _empty_result() -> dict:
    return {
        "threat_level": "LOW",
        "events": [],
        "is_safe": False,
        "incident_type": "None",
        "reasons": "No speech detected in this window.",
    }


ai_threat_service = AIThreatService()
