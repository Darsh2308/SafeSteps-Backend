import json
import pydantic
import httpx
from langsmith import traceable
from app.config import settings
from app.utils.logger import Logger

try:
    from google import genai
    from google.genai import types as genai_types
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False

# ── Structured output schemas ──────────────────────────────────────────────────

class SafetyResponseSchema(pydantic.BaseModel):
    guidance: str
    questions: list[str]
    recommendations: list[str]

class IncidentReportSchema(pydantic.BaseModel):
    threatLevel: str
    incidentType: str
    summary: str
    actionsTaken: list[str]
    recommendations: list[str]

# ── Language map ──────────────────────────────────────────────────────────────

_LANGUAGE_NAMES = {
    "en-IN": "English",
    "hi-IN": "Hindi (हिंदी)",
    "mr-IN": "Marathi (मराठी)",
    "bn-IN": "Bengali (বাংলা)",
    "ta-IN": "Tamil (தமிழ்)",
    "te-IN": "Telugu (తెలుగు)",
    "kn-IN": "Kannada (ಕನ್ನಡ)",
    "ml-IN": "Malayalam (മലയാളം)",
    "gu-IN": "Gujarati (ગુજરાતી)",
    "pa-IN": "Punjabi (ਪੰਜਾਬੀ)",
}

# ── Prompts ────────────────────────────────────────────────────────────────────

_SAFETY_SYSTEM_PROMPT = (
    "You are SafeSteps AI, an advanced multilingual personal safety assistant. "
    "You receive safety messages or descriptions of emergency situations. "
    "Respond in a calm, clear, and reassuring tone. "
    "CRITICAL LANGUAGE RULE: You MUST detect the language of the user's message and reply "
    "in that exact same language. If the user writes in Hindi, respond fully in Hindi. "
    "If in Marathi, respond fully in Marathi. If in English, respond in English. "
    "Provide immediate guidance, ask clarifying safety questions, and give action recommendations. "
    "Return output strictly matching the structured JSON schema."
)

_REPORT_SYSTEM_PROMPT = (
    "You are SafeSteps AI. Analyze the emergency logs (transcripts and logged timeline events). "
    "Compile a final structured Incident Report with incident classification, summary, actions taken, and recommendations. "
    "Conform strictly to the JSON incident report schema."
)

_GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODEL = "llama-3.1-8b-instant"


class AIService:
    def __init__(self):
        # Groq client (primary — Gemma2-9b-it)
        self._groq_ready = bool(settings.GROQ_API_KEY)
        if self._groq_ready:
            Logger.info(f"AI Service: Groq/{_GROQ_MODEL} client ready.")
        else:
            Logger.warn("GROQ_API_KEY not set. Groq/Gemma fallback unavailable.")

        # Gemini client (secondary)
        self._gemini_client = None
        if _GENAI_AVAILABLE and settings.GEMINI_API_KEY:
            try:
                self._gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
                Logger.info("AI Service: Gemini (google-genai) client ready as secondary.")
            except Exception as e:
                Logger.error(f"Failed to initialize Gemini client: {e}")
        elif not _GENAI_AVAILABLE:
            Logger.warn("google-genai not installed — Gemini secondary unavailable.")

    # ── Public API ─────────────────────────────────────────────────────────────

    @traceable(name="Generate Safety Response", run_type="llm")
    async def generate_safety_response(self, message: str, threat_level: str = "LOW", history: list = None, language: str = "en-IN") -> dict:
        """
        Returns: { "guidance": str, "questions": list[str], "recommendations": list[str] }
        Tries Groq/Gemma first, then Gemini, then mock.
        language: BCP-47 code (e.g. "hi-IN", "mr-IN", "en-IN") — LLM is instructed to reply in this language.
        """
        lang_name = _LANGUAGE_NAMES.get(language, "the same language as the user's message")
        prompt = (
            f"RESPOND IN: {lang_name}\n"
            f"Current Session Threat Level: {threat_level}\n"
            f"User Message: {message}"
        )

        # 1. Try Groq / Gemma
        if self._groq_ready:
            try:
                return await self._call_groq(_SAFETY_SYSTEM_PROMPT, prompt, SafetyResponseSchema)
            except Exception as e:
                Logger.error(f"Groq safety response failed: {e}. Trying Gemini.")

        # 2. Try Gemini
        if self._gemini_client:
            try:
                return await self._call_gemini(_SAFETY_SYSTEM_PROMPT, prompt, SafetyResponseSchema)
            except Exception as e:
                Logger.error(f"Gemini safety response failed: {e}. Falling back to mock.")

        # 3. Mock
        return self._mock_safety_response(message, threat_level)

    @traceable(name="Generate Incident Report", run_type="llm")
    async def generate_report(self, session_id: str, transcripts: list, events: list, threat_level: str = "LOW") -> dict:
        """
        Returns: { "threatLevel": str, "incidentType": str, "summary": str,
                   "actionsTaken": list[str], "recommendations": list[str] }
        Tries Groq/Gemma first, then Gemini, then mock.
        """
        user_content = json.dumps({
            "threat_level": threat_level,
            "transcripts": transcripts,
            "events": events
        })

        # 1. Try Groq / Gemma
        if self._groq_ready:
            try:
                return await self._call_groq(_REPORT_SYSTEM_PROMPT, user_content, IncidentReportSchema)
            except Exception as e:
                Logger.error(f"Groq report generation failed: {e}. Trying Gemini.")

        # 2. Try Gemini
        if self._gemini_client:
            try:
                return await self._call_gemini(_REPORT_SYSTEM_PROMPT, user_content, IncidentReportSchema)
            except Exception as e:
                Logger.error(f"Gemini report generation failed: {e}. Falling back to mock.")

        # 3. Mock
        return self._mock_report(transcripts, events, threat_level)

    # ── Internal callers ───────────────────────────────────────────────────────

    async def _call_groq(self, system: str, user: str, schema_cls: type) -> dict:
        """POST to Groq OpenAI-compatible endpoint with JSON mode."""
        field_names = list(schema_cls.model_fields.keys())
        schema_hint = f"Respond ONLY with a valid JSON object with exactly these keys: {field_names}"

        payload = {
            "model": _GROQ_MODEL,
            "messages": [
                {"role": "system", "content": f"{system}\n\n{schema_hint}"},
                {"role": "user", "content": user}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.3,
            "max_tokens": 1024
        }
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(_GROQ_API_URL, json=payload, headers=headers)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return json.loads(content)

    async def _call_gemini(self, system: str, user: str, schema_cls: type) -> dict:
        """Call Gemini with structured output via google-genai SDK."""
        response = await self._gemini_client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=user,
            config=genai_types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                response_schema=schema_cls,
            )
        )
        return json.loads(response.text)

    # ── Mock fallbacks ─────────────────────────────────────────────────────────

    def _mock_safety_response(self, message: str, threat_level: str) -> dict:
        msg = message.lower()

        guidance = "Please stay calm. Find a brightly lit public place if possible, and walk toward people."
        questions = ["Can you see a safe place or store nearby?", "Are you alone or with others?"]
        recommendations = ["Move towards a crowded area.", "Prepare your phone to dial emergency contacts."]

        if "crash" in msg or "accident" in msg:
            guidance = "Ensure you are in a safe location away from oncoming traffic. Take a deep breath."
            questions = ["Are you or anyone else injured?", "Is the vehicle smoking or leaking fuel?"]
            recommendations = ["Turn on vehicle hazard lights.", "Call local emergency services immediately."]
        elif "follow" in msg or "behind" in msg:
            guidance = "Do not go home directly. Walk towards a public shop, police station, or gas station."
            questions = ["Is the person keeping their distance or approaching?", "Are you on a well-lit street?"]
            recommendations = ["Cross the street to check if they match your direction.", "Keep your primary emergency contacts on speed dial."]
        elif threat_level in ["HIGH", "CRITICAL"]:
            guidance = "We have escalated your threat level status. Prepare to make immediate safety contacts."
            questions = ["Can you safely call the police?", "Do you need us to trigger auto-calls to your contacts?"]
            recommendations = ["Seek immediate shelter.", "Keep SafeSteps active so we can track your coordinates."]

        return {"guidance": guidance, "questions": questions, "recommendations": recommendations}

    def _mock_report(self, transcripts: list, events: list, threat_level: str) -> dict:
        incident_type = "Suspicious Alert"
        summary = "An SOS alert was triggered by the user. "
        transcripts_str = " ".join(transcripts).lower()

        if "crash" in transcripts_str or any("Crash" in e for e in events):
            incident_type = "Vehicle Accident"
            summary += "The session transcripts and events indicate a high-impact crash or vehicular accident."
        elif "follow" in transcripts_str or any("Scream" in e for e in events):
            incident_type = "Personal Security Threat"
            summary += "A personal security alert was generated due to suspicious activity, screaming, or a follower."
        else:
            summary += "The session was concluded without any severe acoustic safety events detected."

        actions = ["SOS Triggered", "Emergency session initialized"]
        if threat_level in ["HIGH", "CRITICAL"]:
            actions.extend(["SMS notifications queued for primary emergency contacts", "Live GPS tracking actively enabled"])

        recs = [
            "Review your default safety sensitivity settings.",
            "Keep emergency contact numbers updated with the primary tag."
        ]
        if incident_type == "Vehicle Accident":
            recs.append("Check vehicle dashboard warnings and share insurance information.")
        else:
            recs.append("Avoid walking through unlit corridors alone late at night.")

        return {
            "threatLevel": threat_level,
            "incidentType": incident_type,
            "summary": summary,
            "actionsTaken": actions,
            "recommendations": recs
        }


ai_service = AIService()
