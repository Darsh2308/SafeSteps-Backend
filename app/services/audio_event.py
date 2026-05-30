from datetime import datetime

# ── Multilingual keyword banks ─────────────────────────────────────────────────

_SCREAM_KEYWORDS = [
    # English — specific distress phrases only (not bare "help" which is too common)
    "help me", "please help", "somebody help", "screaming", "no no no",
    "please don't", "let me go", "get away from me", "stop stop",
    # Hindi — Devanagari
    "बचाओ", "छोड़ो", "नहीं नहीं", "मत करो", "चिल्लाना", "मुझे छोड़ो",
    # Hindi — Roman
    "bachao", "chhodo", "nahi nahi", "mat karo", "mujhe chhodo",
    # Marathi — Devanagari
    "वाचवा", "सोडा", "नको नको", "करू नका", "मला सोडा",
    # Marathi — Roman
    "vachva", "soda", "nako nako", "mala soda",
]

_AGGRESSION_KEYWORDS = [
    # English
    "kill", "die", "fight", "shut up", "don't touch", "steal", "rob", "knife", "gun",
    # Hindi — Devanagari
    "मार दूंगा", "मरो", "लड़ाई", "चुप रहो", "मत छुओ", "चोरी", "लूट", "चाकू", "बंदूक",
    # Hindi — Roman
    "maar dunga", "maro", "ladai", "chup raho", "mat chuo", "chori", "loot", "chaaku", "bandook",
    # Marathi — Devanagari
    "मारतो", "मरा", "भांडण", "गप्प बस", "हात लावू नका", "चोरी", "लूट", "चाकू", "बंदूक",
    # Marathi — Roman
    "maarto", "mara", "bhandan", "gapp bas", "haat lavu naka", "chori", "loot", "chaaku", "bandook",
]

_CRYING_KEYWORDS = [
    # English
    "cry", "crying", "sobbing", "scared", "afraid", "hurting", "please help",
    # Hindi — Devanagari
    "रो रहा", "रो रही", "रोना", "डर", "डरी हुई", "दर्द", "मदद करो",
    # Hindi — Roman
    "ro raha", "ro rahi", "rona", "dar", "dari hui", "dard", "madad karo",
    # Marathi — Devanagari
    "रडत आहे", "रडणे", "भीती", "घाबरलो", "घाबरली", "दुखत", "मदत करा",
    # Marathi — Roman
    "radat aahe", "radne", "bhiti", "ghabaralo", "ghabarali", "dukhta", "madat kara",
]

_CRASH_KEYWORDS = [
    # English
    "crash", "accident", "hit my car", "collision", "smashed", "brakes",
    # Hindi — Devanagari
    "हादसा", "दुर्घटना", "टक्कर", "गाड़ी", "ब्रेक",
    # Hindi — Roman
    "hadsa", "durghatna", "takkar", "gaadi", "brake",
    # Marathi — Devanagari
    "अपघात", "धडक", "गाडी", "ब्रेक",
    # Marathi — Roman
    "apaghat", "dhadak", "gaadi", "brake",
]

_BREATHING_KEYWORDS = [
    # English
    "pant", "breath", "gasping", "huffing",
    # Hindi — Devanagari
    "सांस", "दम", "हांफ",
    # Hindi — Roman
    "sans", "dam", "haanf",
    # Marathi — Devanagari
    "श्वास", "दम",
    # Marathi — Roman
    "shwas", "dam",
]


def _keyword_hit(text_lower: str, text_raw: str, keywords: list) -> bool:
    """Match ASCII keywords case-insensitively; match Devanagari in original text."""
    return (
        any(k.lower() in text_lower for k in keywords if k.isascii()) or
        any(k in text_raw for k in keywords if not k.isascii())
    )


class AudioEventDetector:
    def detect_events(self, audio_bytes: bytes, transcript: str = "") -> list:
        """
        Analyzes audio chunks (PCM 16-bit Mono) and speech transcripts to identify
        safety-critical audio events. Supports English, Hindi, and Marathi.

        Returns:
            list: List of dicts with { "event_type": str, "confidence": float, "timestamp": datetime }
        """
        events = []
        if not audio_bytes and not transcript:
            return events

        timestamp = datetime.utcnow()

        # Energy-only dBFS detection removed — too many false positives on normal speech
        # without an ML classifier (YAMNet). Will be re-enabled in v2 with YAMNet.
        # Detection is now keyword-only until YAMNet is integrated.

        # Multilingual keyword-based semantic analysis
        if transcript:
            text_lower = transcript.lower()
            text_raw = transcript  # preserve Devanagari

            if _keyword_hit(text_lower, text_raw, _SCREAM_KEYWORDS):
                events.append({"event_type": "Screams", "confidence": 0.90, "timestamp": timestamp})

            if _keyword_hit(text_lower, text_raw, _AGGRESSION_KEYWORDS):
                events.append({"event_type": "Aggression", "confidence": 0.85, "timestamp": timestamp})

            if _keyword_hit(text_lower, text_raw, _CRYING_KEYWORDS):
                events.append({"event_type": "Crying", "confidence": 0.80, "timestamp": timestamp})

            if _keyword_hit(text_lower, text_raw, _CRASH_KEYWORDS):
                events.append({"event_type": "Vehicle Crash", "confidence": 0.95, "timestamp": timestamp})

            if _keyword_hit(text_lower, text_raw, _BREATHING_KEYWORDS):
                events.append({"event_type": "Heavy Breathing", "confidence": 0.70, "timestamp": timestamp})

        # Deduplicate — keep highest confidence per event type
        unique: dict = {}
        for e in events:
            et = e["event_type"]
            if et not in unique or e["confidence"] > unique[et]["confidence"]:
                unique[et] = e

        return list(unique.values())


audio_event_detector = AudioEventDetector()
