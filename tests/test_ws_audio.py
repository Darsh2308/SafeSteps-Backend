import pytest
from fastapi.testclient import TestClient

def test_websocket_audio_ingest(client):
    # 1. Register and get token
    client.post("/auth/send-otp", json={"phoneNumber": "+15551119999"})
    res_auth = client.post("/auth/verify-otp", json={
        "phoneNumber": "+15551119999",
        "code": "123456"
    })
    headers = {"Authorization": f"Bearer {res_auth.json()['token']}"}

    # 2. Start session
    r_session = client.post("/emergency/start", headers=headers)
    session_id = r_session.json()["session_id"]

    # 3. Connect to WebSocket
    with client.websocket_connect(f"/ws/audio/{session_id}") as websocket:
        # Send 1 chunk of silent 16kHz PCM (16000 bytes = 0.5s)
        silent_pcm = bytes(16000)
        websocket.send_bytes(silent_pcm)
        
        # Connection should stay active and accept chunks
        websocket.send_bytes(silent_pcm)
        
        # WebSocket should not crash and should disconnect cleanly on exit
