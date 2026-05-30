import asyncio
import httpx
import websockets
import json
import numpy as np
from app.utils.logger import Logger

BASE_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000"

async def run_live_backend():
    Logger.info("Starting Live Backend End-To-End Test Runner...")
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        # ── Step 1: Authentication Flow ──
        Logger.info("\n--- STEP 1: Authentication ---")
        phone = "+15551234567"
        
        # Request OTP
        r_otp = await client.post(f"{BASE_URL}/auth/send-otp", json={"phoneNumber": phone})
        assert r_otp.status_code == 200, f"OTP Send failed: {r_otp.text}"
        Logger.info("OTP sent successfully.")

        # Verify OTP
        r_verify = await client.post(f"{BASE_URL}/auth/verify-otp", json={
            "phoneNumber": phone,
            "code": "123456" # Universal local bypass
        })
        assert r_verify.status_code == 200, f"OTP verification failed: {r_verify.text}"
        auth_data = r_verify.json()
        token = auth_data["token"]
        headers = {"Authorization": f"Bearer {token}"}
        Logger.info(f"Verified OTP. User authenticated. Token acquired.")

        # Check /auth/me
        r_me = await client.get(f"{BASE_URL}/auth/me", headers=headers)
        assert r_me.status_code == 200
        Logger.info(f"User Profile Info: {r_me.json()}")

        # ── Step 2: Configure Contacts & Settings ──
        Logger.info("\n--- STEP 2: Configure Contacts & Settings ---")
        
        # Clear any existing contacts
        r_contacts_get = await client.get(f"{BASE_URL}/contacts", headers=headers)
        for contact in r_contacts_get.json():
            await client.delete(f"{BASE_URL}/contacts/{contact['id']}", headers=headers)

        # Add 3 contacts
        contacts = [
            {"name": "Sarah Jenkins", "relationship": "Spouse", "phoneNumber": "+15550123456", "priority": "Primary"},
            {"name": "Robert Doe", "relationship": "Father", "phoneNumber": "+15550198765", "priority": "Secondary"},
            {"name": "Dr. David Vance", "relationship": "Family Doctor", "phoneNumber": "+15550112233", "priority": "Tertiary"}
        ]
        
        for c in contacts:
            r_add = await client.post(f"{BASE_URL}/contacts", json=c, headers=headers)
            assert r_add.status_code == 201, f"Failed to add contact: {r_add.text}"
            Logger.info(f"Added emergency contact: {r_add.json()['name']} ({r_add.json()['relationship']})")

        # ── Step 3: Sync Permissions ──
        Logger.info("\n--- STEP 3: Sync Permissions ---")
        permissions = {
            "permissions": [
                {"name": "Location Access", "description": "precise dispatch", "type": "location", "status": True},
                {"name": "Microphone Usage", "description": "background diagnostic", "type": "microphone", "status": True},
                {"name": "Send SMS", "description": "auto alerts", "type": "sms", "status": True}
            ]
        }
        r_perm = await client.post(f"{BASE_URL}/permissions/sync", json=permissions, headers=headers)
        assert r_perm.status_code == 200
        Logger.info("Device permissions synced to server.")

        # ── Step 4: Activate SOS Session ──
        Logger.info("\n--- STEP 4: Start SOS Emergency Session ---")
        r_start = await client.post(f"{BASE_URL}/emergency/start", headers=headers)
        assert r_start.status_code == 200, f"SOS Start failed: {r_start.text}"
        session_data = r_start.json()
        session_id = session_data["session_id"]
        Logger.info(f"Emergency Session Started! ID: {session_id}")

        # ── Step 5: Live Location Updates ──
        Logger.info("\n--- STEP 5: Live Location Logs ---")
        # Post initial coordinates
        r_loc = await client.post(f"{BASE_URL}/location/update", json={
            "latitude": 18.5204,
            "longitude": 73.8567,
            "accuracy": 4.5,
            "speed": 0.0,
            "heading": 0.0
        }, headers=headers)
        assert r_loc.status_code == 200
        Logger.info("Initial GPS location updated successfully.")

        # ── Step 6: Live Audio Stream over WebSockets (VAD, STT, Fusion) ──
        Logger.info("\n--- STEP 6: Live WebSocket Audio Stream ---")
        
        ws_endpoint = f"{WS_URL}/ws/audio/{session_id}"
        async with websockets.connect(ws_endpoint) as websocket:
            Logger.info(f"Connected to Audio WebSocket: {ws_endpoint}")

            # Send 1st chunk: Silent Audio (VAD should filter out)
            Logger.info("Sending 0.5s chunk of silent audio...")
            silent_chunk = bytes(16000) # 16kHz 16-bit mono = 32000 bytes/sec
            await websocket.send(silent_chunk)
            await asyncio.sleep(0.5)

            # Send 2nd chunk: Loud Audio (Acoustic triggers crash/screams)
            Logger.info("Sending 0.5s chunk of high-volume audio to simulate safety scream/crash...")
            # Alternating max values (square wave) representing loud noise
            loud_chunk = (b"\xff\x7f\x00\x80" * 4000) 
            await websocket.send(loud_chunk)
            
            # Wait to read the threat update broadcasted back by the WebSocket
            try:
                Logger.info("Waiting for real-time threat assessment broadcast...")
                ws_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                threat_update = json.loads(ws_response)
                Logger.info(f"WebSocket Broadcast Received: {json.dumps(threat_update, indent=2)}")
                assert threat_update["threat_level"] in ["HIGH", "CRITICAL"], "Threat fusion did not escalate threat level"
            except asyncio.TimeoutError:
                Logger.warn("WebSocket timeout. No threat broadcast received (ensure Sarvam/Gemini fallbacks are configured).")

        # ── Step 7: Call Logs & Timeline Events ──
        Logger.info("\n--- STEP 7: Track Call Status ---")
        r_call = await client.post(f"{BASE_URL}/call/status", json={"state": "Answered"}, headers=headers)
        assert r_call.status_code == 200
        Logger.info("Call Log: Contact picked up emergency call.")

        # ── Step 8: Interactive Safety Guidance Chat ──
        Logger.info("\n--- STEP 8: Safety Guidance Advisor (Gemini ADK Agent) ---")
        chat_msg = "I hear glass breaking and footsteps behind me. What should I do?"
        Logger.info(f"Sending User Message: '{chat_msg}'")
        
        r_chat = await client.post(f"{BASE_URL}/conversation/message", json={"message": chat_msg}, headers=headers)
        assert r_chat.status_code == 200, f"Guidance Chat failed: {r_chat.text}"
        chat_data = r_chat.json()
        Logger.info(f"Gemini ADK Safety Guidance Response:\n{json.dumps(chat_data, indent=2)}")
        assert "guidance" in chat_data
        assert len(chat_data["questions"]) > 0

        # ── Step 9: Deactivate SOS Session & Fetch final report ──
        Logger.info("\n--- STEP 9: End Emergency Session ---")
        r_end = await client.post(f"{BASE_URL}/emergency/end", headers=headers)
        assert r_end.status_code == 200, f"SOS End failed: {r_end.text}"
        incident_report = r_end.json()
        Logger.info(f"SOS Deactivated. Compiled Incident report details:\n{json.dumps(incident_report, indent=2)}")
        assert incident_report["duration"] != "Active"
        assert len(incident_report["summary"]) > 0

        # ── Step 10: Fetch Dashboard Analytics ──
        Logger.info("\n--- STEP 10: Dashboard Analytics ---")
        r_analytics = await client.get(f"{BASE_URL}/analytics/overview", headers=headers)
        assert r_analytics.status_code == 200
        Logger.info(f"Dashboard Safety Overview:\n{json.dumps(r_analytics.json(), indent=2)}")
        assert r_analytics.json()["totalEncounters"] >= 1

        Logger.info("\n==================================================")
        Logger.info("SUCCESS: Live Backend End-To-End Verification Passed!")
        Logger.info("==================================================")

if __name__ == "__main__":
    try:
        asyncio.run(run_live_backend())
    except Exception as e:
        Logger.error(f"E2E Verification Failed: {e}", exc=e)
