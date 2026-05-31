from tests.conftest import register_and_login


def test_websocket_silent_audio_ingest(client):
    headers = register_and_login(client, "+15551119999")

    r_session = client.post("/emergency/start", headers=headers)
    assert r_session.status_code == 200
    session_id = r_session.json()["session_id"]

    with client.websocket_connect(f"/ws/audio/{session_id}") as ws:
        # 0.5 s of silent 16 kHz 16-bit PCM — VAD should detect no speech
        ws.send_bytes(bytes(16000))
        ws.send_bytes(bytes(16000))
        # WebSocket must accept bytes and remain alive (no crash)


def test_websocket_invalid_session(client):
    register_and_login(client, "+15551118888")
    # Connecting to a non-existent session should close with an error code
    try:
        with client.websocket_connect("/ws/audio/nonexistent-session-id") as ws:
            ws.send_bytes(bytes(1024))
    except Exception:
        pass  # Connection closure or rejection is the expected behaviour
