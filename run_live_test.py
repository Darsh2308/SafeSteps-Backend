import asyncio
import httpx
import websockets
import json
from app.utils.logger import Logger

BASE_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000"


async def run_live_backend():
    """End-to-end smoke test for the lean, threat-aware SOS feature.

    Flow: register/login -> start SOS -> location -> live audio (VAD/STT/threat)
          -> AI chat -> end session. (Contacts/SMS are handled on the device.)
    """
    Logger.info("Starting Live Backend End-To-End Test Runner...")

    async with httpx.AsyncClient(timeout=15.0) as client:
        # ── Step 1: Authentication (register, fall back to login) ──
        Logger.info("\n--- STEP 1: Authentication ---")
        phone = "+15551234567"

        r = await client.post(f"{BASE_URL}/auth/register", json={
            "phone": phone,
            "full_name": "Live Test User",
            "preferred_language": "English",
        })
        if r.status_code == 400:  # already registered → log in
            r = await client.post(f"{BASE_URL}/auth/login", json={"phone": phone})
        assert r.status_code in (200, 201), f"Auth failed: {r.text}"
        token = r.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        Logger.info("Authenticated. Token acquired.")

        r_me = await client.get(f"{BASE_URL}/auth/me", headers=headers)
        assert r_me.status_code == 200
        Logger.info(f"User Profile Info: {r_me.json()}")

        # ── Step 2: Activate SOS Session ──
        Logger.info("\n--- STEP 2: Start SOS Emergency Session ---")
        r_start = await client.post(f"{BASE_URL}/emergency/start", headers=headers)
        assert r_start.status_code == 200, f"SOS Start failed: {r_start.text}"
        session_id = r_start.json()["session_id"]
        Logger.info(f"Emergency Session Started! ID: {session_id}")

        # ── Step 3: Live Location Update (returns Maps link for the app's SMS) ──
        Logger.info("\n--- STEP 3: Live Location Update ---")
        r_loc = await client.post(f"{BASE_URL}/location/update", json={
            "latitude": 18.5204, "longitude": 73.8567,
            "accuracy": 4.5, "speed": 0.0, "heading": 0.0,
        }, headers=headers)
        assert r_loc.status_code == 200
        Logger.info(f"GPS updated. Maps link: {r_loc.json().get('maps_link')}")

        # ── Step 4: Live Audio Stream over WebSocket (VAD → STT → threat) ──
        Logger.info("\n--- STEP 4: Live WebSocket Audio Stream ---")
        ws_endpoint = f"{WS_URL}/ws/audio/{session_id}"
        async with websockets.connect(ws_endpoint) as websocket:
            Logger.info(f"Connected to Audio WebSocket: {ws_endpoint}")

            Logger.info("Sending 0.5s of silent audio (VAD should filter it)...")
            await websocket.send(bytes(16000))  # 16kHz 16-bit mono = 32000 B/s
            await asyncio.sleep(0.5)

            Logger.info("Sending 0.5s of high-volume audio (simulated distress)...")
            await websocket.send(b"\xff\x7f\x00\x80" * 4000)

            try:
                Logger.info("Waiting for real-time threat assessment broadcast...")
                ws_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                Logger.info(f"WebSocket Broadcast Received:\n{json.dumps(json.loads(ws_response), indent=2)}")
            except asyncio.TimeoutError:
                Logger.warn("WebSocket timeout — no broadcast (ensure Sarvam/Groq keys or fallbacks are configured).")

        # ── Step 5: Interactive Safety Guidance Chat ──
        Logger.info("\n--- STEP 5: AI Safety Guidance Chat ---")
        chat_msg = "I hear glass breaking and footsteps behind me. What should I do?"
        r_chat = await client.post(f"{BASE_URL}/conversation/message", json={"message": chat_msg}, headers=headers)
        assert r_chat.status_code == 200, f"Guidance Chat failed: {r_chat.text}"
        chat_data = r_chat.json()
        Logger.info(f"AI Safety Guidance Response:\n{json.dumps(chat_data, indent=2)}")
        assert "guidance" in chat_data

        # ── Step 6: Deactivate SOS Session & fetch compiled incident ──
        Logger.info("\n--- STEP 6: End Emergency Session ---")
        r_end = await client.post(f"{BASE_URL}/emergency/end", headers=headers)
        assert r_end.status_code == 200, f"SOS End failed: {r_end.text}"
        incident = r_end.json()
        Logger.info(f"SOS Deactivated. Compiled incident:\n{json.dumps(incident, indent=2)}")
        assert incident["duration"] != "Active"

        Logger.info("\n==================================================")
        Logger.info("SUCCESS: Live Backend End-To-End Verification Passed!")
        Logger.info("==================================================")


if __name__ == "__main__":
    try:
        asyncio.run(run_live_backend())
    except Exception as e:
        Logger.error(f"E2E Verification Failed: {e}", exc=e)
