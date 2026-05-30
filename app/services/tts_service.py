import httpx
from app.config import settings
from app.utils.logger import Logger

_SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
_DEFAULT_SPEAKER = "anushka"
_MODEL = "bulbul:v1"

# Valid speakers as of 2026-05: meera was retired.
# anushka = female (Indian English, Hindi, Marathi, Bengali, Gujarati)
# abhilash = male (South Indian languages: Tamil, Telugu, Kannada, Malayalam)
_SPEAKER_MAP = {
    "en-IN": "anushka",
    "hi-IN": "anushka",
    "mr-IN": "anushka",
    "bn-IN": "anushka",
    "gu-IN": "anushka",
    "pa-IN": "anushka",
    "ta-IN": "abhilash",
    "te-IN": "abhilash",
    "kn-IN": "abhilash",
    "ml-IN": "abhilash",
}


class TTSService:
    def __init__(self):
        self.api_key = settings.SARVAM_API_KEY
        if self.api_key:
            Logger.info("TTS Service: Sarvam TTS client ready.")
        else:
            Logger.warn("SARVAM_API_KEY not set. TTS will return None (mobile falls back to Android TTS).")

    async def synthesize(self, text: str, language: str = "en-IN") -> bytes | None:
        """
        Converts text to speech using Sarvam Bulbul TTS.

        Returns raw WAV audio bytes, or None if unavailable (mobile handles fallback via Android TTS).

        Args:
            text: Text to speak (max ~500 chars per call).
            language: BCP-47 language code (en-IN, hi-IN, mr-IN, etc.)

        Returns:
            bytes: WAV audio data, or None on failure.
        """
        if not text or not text.strip():
            return None

        if not self.api_key:
            Logger.info("TTS Service: No API key — skipping synthesis (mobile uses Android TTS).")
            return None

        speaker = _SPEAKER_MAP.get(language, _DEFAULT_SPEAKER)

        payload = {
            "inputs": [text[:500]],
            "target_language_code": language,
            "speaker": speaker,
            "model": _MODEL,
        }
        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(_SARVAM_TTS_URL, json=payload, headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                import base64
                audio_b64 = data.get("audios", [None])[0]
                if audio_b64:
                    Logger.info(f"TTS Service: Synthesized {len(text)} chars in {language}.")
                    return base64.b64decode(audio_b64)
                Logger.warn("TTS Service: Sarvam returned 200 but no audio payload.")
                return None

            Logger.error(f"TTS Service: Sarvam returned [{resp.status_code}]: {resp.text}")
            return None

        except Exception as e:
            Logger.error(f"TTS Service: Request failed: {e}")
            return None


tts_service = TTSService()
