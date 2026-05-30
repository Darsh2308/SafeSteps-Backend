from typing import List, Dict
from app.utils.logger import Logger

# ── Multilingual keyword banks ─────────────────────────────────────────────────
# Each list contains English, Hindi (Devanagari + Roman), and Marathi (Devanagari + Roman).
# Sarvam returns Devanagari for hi-IN / mr-IN, so both scripts are included.

_SAFE_KEYWORDS = [
    # English
    "i am safe", "i'm safe", "i am okay", "i'm okay", "i'm fine", "i am fine",
    "false alarm", "all clear", "everything is fine", "everything is okay",
    "police is here", "police officer", "police arrived", "help has arrived",
    "i reached home", "cancel sos", "i am home", "danger has passed",
    # Hindi — Devanagari
    "मैं सुरक्षित हूं", "मैं ठीक हूं", "सब ठीक है", "पुलिस आ गई", "मैं घर पहुंच गया",
    # Hindi — Roman
    "mai surakshit hun", "mai theek hun", "sab theek hai", "police aa gayi",
    # Marathi — Devanagari
    "मी सुरक्षित आहे", "मी ठीक आहे", "सगळं ठीक आहे", "पोलीस आले",
    # Marathi — Roman
    "mi surakshit aahe", "mi theek aahe", "sagal theek aahe", "police aale",
]

_CRITICAL_KEYWORDS = [
    # English
    "kill", "stab", "gun", "shoot", "choking", "can't breathe", "accident", "dying",
    # Hindi — Devanagari
    "मार दूंगा", "चाकू मारूंगा", "बंदूक", "गोली", "दम घुट", "सांस नहीं", "हादसा", "मर रहा", "मर रही",
    # Hindi — Roman transliteration (Sarvam may output either)
    "maar dunga", "chaaku", "bandook", "goli", "dam ghut", "sans nahi", "hadsa", "mar raha",
    # Marathi — Devanagari
    "मारतो", "चाकू", "बंदूक", "गोळी", "श्वास घेता येत नाही", "अपघात", "मरत आहे",
    # Marathi — Roman transliteration
    "maarto", "bandook", "goli", "shwas", "apaghat", "marat aahe",
]

_HIGH_KEYWORDS = [
    # English
    "follow", "stalk", "run", "chasing", "get away", "touch", "scared", "afraid", "police", "help",
    # Hindi — Devanagari
    "पीछे आ रहा", "पीछे आ रही", "भागो", "पुलिस", "बचाओ", "मदद", "मदद करो", "डर", "छोड़ो", "मत छुओ",
    # Hindi — Roman
    "peeche aa raha", "bhaago", "bachao", "madad", "madad karo", "dar", "chhodo", "mat chuo",
    # Marathi — Devanagari
    "मागे येत आहे", "पळा", "पोलीस", "वाचवा", "मदत करा", "मदत", "भीती", "सोडा", "हात लावू नका",
    # Marathi — Roman
    "mage yet aahe", "pala", "police", "vachva", "madat kara", "bhiti", "soda", "haat lavu naka",
]


class ThreatFusionEngine:
    def assess_threat(
        self,
        transcripts: List[str],
        audio_events: List[str],
        speeds: List[float],
        call_states: List[str],
        prior_threat: str = "LOW"
    ) -> Dict:
        """
        Synthesizes multiple telemetry vectors to calculate current emergency severity.
        Supports English, Hindi, and Marathi transcript keyword detection.

        Returns:
            dict: { "threat_level": str, "confidence": float, "reasons": str }
        """
        threat_level = "LOW"
        confidence = 0.5
        reasons = []

        event_set = set(audio_events)
        call_set = set(call_states)
        # Lowercase for English; keep original for Devanagari (already case-insensitive)
        transcript_text = " ".join(transcripts).lower()
        transcript_raw = " ".join(transcripts)  # preserve Devanagari case

        # 1. Call status
        if "Failed" in call_set:
            reasons.append("Emergency phone call failed to connect.")
            threat_level = "MEDIUM"
            confidence = 0.7

        # 2. GPS speed
        max_speed = max(speeds) if speeds else 0.0
        if max_speed > 80.0:
            reasons.append(f"High-speed movement detected ({max_speed:.1f} km/h).")
            if "Vehicle Crash" in event_set:
                threat_level = "CRITICAL"
                confidence = 0.95
                reasons.append("High-speed movement combined with crash impact noise.")
            else:
                threat_level = "MEDIUM"
                confidence = 0.6

        # 3. Audio events
        if "Vehicle Crash" in event_set and threat_level != "CRITICAL":
            threat_level = "HIGH"
            confidence = 0.85
            reasons.append("Vehicle crash acoustic event detected.")

        if "Screams" in event_set:
            threat_level = "CRITICAL"
            confidence = 0.90
            reasons.append("Acoustic screaming event detected.")

        if "Aggression" in event_set:
            if threat_level != "CRITICAL":
                threat_level = "HIGH"
                confidence = 0.80
            reasons.append("Aggressive speech or hostile noise detected.")

        if "Crying" in event_set:
            if threat_level in ["LOW", "MEDIUM"]:
                threat_level = "MEDIUM"
                confidence = 0.75
            reasons.append("Crying sounds detected.")

        if "Glass Breaking" in event_set:
            if threat_level in ["LOW", "MEDIUM"]:
                threat_level = "MEDIUM"
                confidence = 0.70
            reasons.append("Glass breaking or shatter noise detected.")

        # 4. Multilingual transcript keyword matching
        if transcript_text or transcript_raw:
            # Check critical keywords (English lowercased + Devanagari in original)
            critical_hit = any(k.lower() in transcript_text for k in _CRITICAL_KEYWORDS if k.isascii()) or \
                           any(k in transcript_raw for k in _CRITICAL_KEYWORDS if not k.isascii())

            high_hit = any(k.lower() in transcript_text for k in _HIGH_KEYWORDS if k.isascii()) or \
                       any(k in transcript_raw for k in _HIGH_KEYWORDS if not k.isascii())

            if critical_hit:
                threat_level = "CRITICAL"
                confidence = max(confidence, 0.90)
                reasons.append("Critical emergency keywords identified in speech transcript.")
            elif high_hit:
                if threat_level in ["LOW", "MEDIUM"]:
                    threat_level = "HIGH"
                    confidence = max(confidence, 0.80)
                reasons.append("Safety threat keywords identified in speech transcript.")

        # 5. Safe-word override — explicit de-escalation bypasses prior threat
        safe_hit = any(k in transcript_text for k in _SAFE_KEYWORDS if k.isascii()) or \
                   any(k in transcript_raw for k in _SAFE_KEYWORDS if not k.isascii())
        if safe_hit:
            threat_level = "LOW"
            confidence = 0.95
            reasons = ["User confirmed safety — de-escalating session."]
            Logger.info("Threat Fusion: Safe-word detected — overriding to LOW.")
            # Skip prior_threat preservation below
        else:
            # 6. Prior threat context (prevents sudden drops in genuine emergencies)
            if prior_threat == "CRITICAL" and threat_level != "CRITICAL":
                threat_level = "HIGH"
                confidence = 0.70
                reasons.append("Preserving heightened alert status from prior window.")
            elif prior_threat == "HIGH" and threat_level in ["LOW", "MEDIUM"]:
                threat_level = "MEDIUM"
                confidence = 0.60
                reasons.append("Retaining moderate threat categorization from prior window.")

        if not reasons:
            reasons.append("No active threat triggers identified in current stream.")
            threat_level = "LOW"
            confidence = 0.5

        joined_reasons = "; ".join(reasons)
        Logger.info(f"Threat Fusion: {threat_level} (conf: {confidence:.2f}) — {joined_reasons}")

        return {
            "threat_level": threat_level,
            "confidence": confidence,
            "reasons": joined_reasons
        }


threat_fusion_engine = ThreatFusionEngine()
