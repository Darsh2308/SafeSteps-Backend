import pytest
from app.services.vad_service import vad_service
from app.services.stt_service import stt_service
from app.services.audio_event import audio_event_detector
from app.services.threat_fusion import threat_fusion_engine
from app.services.ai_service import ai_service

def test_voice_activity_detection():
    # Test energy-based VAD (or ONNX if loaded) with silent bytes
    silent_pcm = bytes(1024)
    # Energy of silent bytes should be 0.0, so no speech detected
    assert vad_service.is_speech(silent_pcm) is False

    # Simulate loud audio chunk to verify energy-based detection
    # Generates a square wave of max volume 16-bit integer values (32767)
    loud_pcm = (b"\xff\x7f\x00\x80" * 256)
    assert vad_service.is_speech(loud_pcm) is True

def test_stt_transcription():
    # Test that transcribe returns structured dictionary with mock fallback
    mock_pcm = bytes(1000)
    result = stt_service.transcribe(mock_pcm)
    assert "transcript" in result
    assert "language" in result
    assert "confidence" in result
    assert len(result["transcript"]) > 0

def test_audio_event_detection():
    # 1. Text-based keyword event trigger
    events = audio_event_detector.detect_events(bytes(), "Help! I just crashed my car!")
    event_types = [e["event_type"] for e in events]
    assert "Screams" in event_types
    assert "Vehicle Crash" in event_types

    # 2. Peak amplitude event trigger
    # Sending very loud PCM bytes (> -10dBFS) should acoustic trigger Vehicle Crash / Screams
    loud_pcm = (b"\xff\x7f\x00\x80" * 4000)
    events_acoustic = audio_event_detector.detect_events(loud_pcm)
    types_acoustic = [e["event_type"] for e in events_acoustic]
    assert "Vehicle Crash" in types_acoustic
    assert "Screams" in types_acoustic

def test_threat_fusion_engine():
    # Scenario A: Stable/Low Threat
    res_low = threat_fusion_engine.assess_threat(
        transcripts=["Everything is fine", "Just walked into a shop"],
        audio_events=[],
        speeds=[2.5],
        call_states=["Answered"]
    )
    assert res_low["threat_level"] == "LOW"

    # Scenario B: High Speed + Crash acoustic event -> CRITICAL
    res_crash = threat_fusion_engine.assess_threat(
        transcripts=[],
        audio_events=["Vehicle Crash"],
        speeds=[95.0],
        call_states=["Answered"]
    )
    assert res_crash["threat_level"] == "CRITICAL"

    # Scenario C: Scream acoustic event -> CRITICAL
    res_scream = threat_fusion_engine.assess_threat(
        transcripts=[],
        audio_events=["Screams"],
        speeds=[1.2],
        call_states=["Answered"]
    )
    assert res_scream["threat_level"] == "CRITICAL"

    # Scenario D: Threat memory decay (prior CRITICAL)
    res_decay = threat_fusion_engine.assess_threat(
        transcripts=["I'm OK now"],
        audio_events=[],
        speeds=[0.0],
        call_states=["Answered"],
        prior_threat="CRITICAL"
    )
    # Checks context preservation: threat drops to HIGH instead of straight to LOW
    assert res_decay["threat_level"] == "HIGH"

@pytest.mark.asyncio
async def test_ai_guidance_and_reports():
    # Test interactive safety chat builder
    chat_res = await ai_service.generate_safety_response("Someone is walking behind me in the dark corridor")
    assert "guidance" in chat_res
    assert "questions" in chat_res
    assert "recommendations" in chat_res
    assert len(chat_res["questions"]) > 0

    # Test final structured incident report compiler
    report_res = await ai_service.generate_report(
        session_id="dummy_id",
        transcripts=["Help!", "I crashed my car"],
        events=["Vehicle Crash", "Screams"],
        threat_level="CRITICAL"
    )
    assert report_res["threatLevel"] == "CRITICAL"
    assert report_res["incidentType"] == "Vehicle Accident"
    assert len(report_res["summary"]) > 0
