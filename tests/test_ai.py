import pytest
from app.services.vad_service import vad_service
from app.services.stt_service import stt_service
from app.services.audio_event import audio_event_detector
from app.services.threat_fusion import threat_fusion_engine
from app.services.ai_service import ai_service


def test_voice_activity_detection():
    # Silent bytes → no energy → not speech
    assert vad_service.is_speech(bytes(1024)) is False
    # Empty bytes → early-exit guard
    assert vad_service.is_speech(b"") is False
    # Return type is always bool regardless of input
    assert isinstance(vad_service.is_speech(b"\xff\x7f\x00\x80" * 256), bool)


def test_stt_transcription():
    # Garbage bytes send a real Sarvam request; the API may return an empty transcript.
    # We only verify the response structure is correct.
    result = stt_service.transcribe(bytes(1000))
    assert "transcript" in result
    assert "language" in result
    assert "confidence" in result


def test_audio_event_detection():
    # Transcript keyword "crashed" → Vehicle Crash
    events = audio_event_detector.detect_events(bytes(), "I just crashed my car!")
    event_types = [e["event_type"] for e in events]
    assert "Vehicle Crash" in event_types

    # Distress phrase triggers Screams
    events2 = audio_event_detector.detect_events(bytes(), "bachao bachao help me please help")
    assert any(e["event_type"] == "Screams" for e in events2)

    # No transcript + raw bytes only → no events (energy detection removed to avoid false positives)
    events_raw = audio_event_detector.detect_events(b"\xff\x7f\x00\x80" * 4000)
    assert events_raw == []


def test_threat_fusion_engine():
    # Scenario A: Stable/Low Threat
    res_low = threat_fusion_engine.assess_threat(
        transcripts=["Everything is fine", "Just walked into a shop"],
        audio_events=[],
        speeds=[2.5],
        call_states=["Answered"],
    )
    assert res_low["threat_level"] == "LOW"

    # Scenario B: High Speed + Crash acoustic event → CRITICAL
    res_crash = threat_fusion_engine.assess_threat(
        transcripts=[],
        audio_events=["Vehicle Crash"],
        speeds=[95.0],
        call_states=["Answered"],
    )
    assert res_crash["threat_level"] == "CRITICAL"

    # Scenario C: Scream acoustic event → CRITICAL
    res_scream = threat_fusion_engine.assess_threat(
        transcripts=[],
        audio_events=["Screams"],
        speeds=[1.2],
        call_states=["Answered"],
    )
    assert res_scream["threat_level"] == "CRITICAL"

    # Scenario D: Threat memory decay (prior CRITICAL) — drops to HIGH, not LOW
    res_decay = threat_fusion_engine.assess_threat(
        transcripts=["I'm OK now"],
        audio_events=[],
        speeds=[0.0],
        call_states=["Answered"],
        prior_threat="CRITICAL",
    )
    assert res_decay["threat_level"] == "HIGH"


@pytest.mark.asyncio
async def test_ai_guidance_and_reports():
    chat_res = await ai_service.generate_safety_response(
        "Someone is walking behind me in the dark corridor"
    )
    assert "guidance" in chat_res
    assert "questions" in chat_res
    assert "recommendations" in chat_res
    assert len(chat_res["questions"]) > 0

    report_res = await ai_service.generate_report(
        session_id="dummy_id",
        transcripts=["Help!", "I crashed my car"],
        events=["Vehicle Crash", "Screams"],
        threat_level="CRITICAL",
    )
    assert report_res["threatLevel"] == "CRITICAL"
    assert report_res["incidentType"] == "Vehicle Accident"
    assert len(report_res["summary"]) > 0
