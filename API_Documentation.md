# SafeSteps AI — Backend API Documentation

**Version:** 2.1.0 (lean build)
**Base URL (local dev):** `http://localhost:8000`
**Base URL (production):** `https://safesteps-backend-douj.onrender.com`
**Interactive Docs:** `/docs` (Swagger UI)

> **Scope note (2.1.0):** This backend was trimmed to only what the AI-driven, threat-aware
> SOS feature needs. The following modules were **removed**: Profile, Contacts, Permissions,
> Call Status, Reports, standalone Timeline/Transcript endpoints, and Analytics. Their data
> (contacts, the user's name) lives on the device; the app sends all SMS itself via Android
> `SmsManager`. The AI threat pipeline, its offline/low-connectivity **fallback agents**, and
> TTS were all kept.

---

## Table of Contents

1. [Authentication & Headers](#1-authentication--headers)
2. [Auth Endpoints](#2-auth-endpoints)
3. [Emergency Session](#3-emergency-session)
4. [GPS Location](#4-gps-location)
5. [WebSocket — Live Audio (core)](#5-websocket--live-audio-core)
6. [AI Conversation](#6-ai-conversation)
7. [Text-to-Speech (TTS)](#7-text-to-speech-tts)
8. [Notifications](#8-notifications)
9. [Health & Monitoring](#9-health--monitoring)
10. [Error Responses](#10-error-responses)
11. [Fallback Agents (offline / low connectivity)](#11-fallback-agents-offline--low-connectivity)

---

## 1. Authentication & Headers

Every protected endpoint requires a **JWT Bearer token**:

```
Authorization: Bearer <token>
```

The token is returned on **register** or **login** (8-day expiry). Phone number is the unique identity — there is no password and no OTP.

**Unauthenticated endpoints:**
- `POST /auth/register`
- `POST /auth/login`
- `GET /health`, `GET /metrics`, `GET /version`
- `WS /ws/audio/{session_id}` (the `session_id` itself is the credential)

---

## 2. Auth Endpoints

### POST /auth/register

Creates a new user. Phone number is the unique ID.

**Request Body**
```json
{
  "phone": "+919999999999",
  "full_name": "Darsh Patil",
  "age": "24",
  "date_of_birth": "2000-01-15",
  "gender": "Male",
  "blood_group": "O+",
  "medical_notes": "Diabetic",
  "preferred_language": "English"
}
```

Only `phone` and `full_name` are required; the rest are optional.

**Response — 201 Created**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "fullName": "Darsh Patil",
    "age": "24",
    "dateOfBirth": "2000-01-15",
    "gender": "Male",
    "bloodGroup": "O+",
    "medicalNotes": "Diabetic",
    "phone": "+919999999999",
    "preferredLanguage": "English",
    "notificationEnabled": true,
    "privacyEnabled": true,
    "themeDarkMode": true,
    "sosSensitivity": 0.5
  }
}
```

| Status | Condition |
|--------|-----------|
| 400 | Phone already registered → log in instead |

### POST /auth/login

**Request Body**
```json
{ "phone": "+919999999999" }
```

**Response — 200 OK** — same `TokenResponse` shape as register.

| Status | Condition |
|--------|-----------|
| 404 | Phone not registered |

### POST /auth/logout

`Authorization: Bearer <token>`. The client discards the JWT.

```json
{ "success": true, "message": "Logged out successfully" }
```

### GET /auth/me

Returns the authenticated user's profile (the same `user` object shape returned by register/login).

---

## 3. Emergency Session

The core SOS lifecycle: **start → location → audio stream → end**.

### POST /emergency/start

Starts a new SOS session. Any already-active session is closed first.

`Authorization: Bearer <token>` · no body.

**Response — 200 OK**
```json
{
  "session_id": "cfc004e0-3c52-40dd-8ddc-dffd696b4ab9",
  "tracking_id": "8b3f2a1c-...",
  "created_at": "2026-05-30T14:35:22.000Z"
}
```

> **Store `session_id`** — required for the WebSocket and location updates.

### POST /emergency/end

Ends the active session and returns a compiled incident summary.

`Authorization: Bearer <token>` · no body.

> **Note (2.1.0):** End no longer runs a separate AI report-generation step. The returned
> `severity` / `summary` / `incidentType` are derived from the **live threat assessments**
> recorded during the session. The "safe" SMS is sent by the app via Android `SmsManager`.

**Response — 200 OK** — `LoggedIncidentSchema`:
```json
{
  "id": "cfc004e0-...",
  "date": "2026-05-30",
  "startTime": "14:35:22",
  "endTime": "14:47:10",
  "duration": "11m 48s",
  "severity": "HIGH",
  "incidentType": "SOS Activation",
  "summary": "User describes being followed and expresses fear",
  "actionsPerformed": ["SOS Activated"],
  "timeline": [ ... ],
  "transcript": [ ... ]
}
```

### GET /emergency/current

Returns the active session (same shape as `/start`) or `null`.

### GET /emergency/incidents · GET /emergency/history

Both return an array of `LoggedIncidentSchema` for the authenticated user, newest first.

### GET /emergency/{session_id}

Returns a single `LoggedIncidentSchema` by id.

### POST /emergency/trigger

Alias of `/start` that returns the compiled `LoggedIncidentSchema`.

---

## 4. GPS Location

### POST /location/update

`Authorization: Bearer <token>`

**Request Body**
```json
{ "latitude": 19.0760, "longitude": 72.8777, "accuracy": 5.0, "speed": 0.0, "heading": 0.0 }
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `latitude` | float | ✅ | — |
| `longitude` | float | ✅ | — |
| `accuracy` | float | ❌ | meters |
| `speed` | float | ❌ | **m/s** (km/h ÷ 3.6). Sustained >80 m/s combined with a crash event escalates threat in the WebSocket pipeline |
| `heading` | float | ❌ | degrees 0–360 |

**Response — 200 OK**
```json
{ "success": true, "maps_link": "https://maps.google.com/?q=19.076,72.8777", "is_first_update": true }
```

> On `is_first_update: true`, the app sends the SOS SMS via Android `SmsManager` using `maps_link`.

### GET /location/{session_id} · GET /location/history/{session_id}

Latest location, and the full movement trail, for a session.

---

## 5. WebSocket — Live Audio (core)

This is the heart of the feature: the user speaks, the backend transcribes and classifies the threat, and pushes the result back so the app can adapt its SOS SMS.

### WS /ws/audio/{session_id}

- **No auth header** — the `session_id` is the credential.
- **Protocol:** binary WebSocket.
- **Audio format:** raw PCM, 16 kHz, 16-bit signed, mono.

**Connection URL**
```
wss://safesteps-backend-douj.onrender.com/ws/audio/{session_id}
ws://localhost:8000/ws/audio/{session_id}
```

### Sending audio (client → server)

Send raw PCM bytes as binary messages. Recommended chunk size **4096 samples** (256 ms at 16 kHz). The backend gates each chunk through VAD, accumulates speech, and runs STT after ~1.5 s of trailing silence (with a ~3 s STT cooldown).

### Receiving messages (server → client)

A JSON message is pushed after each STT + AI analysis cycle:

```json
{
  "type": "threat_update",
  "session_id": "cfc004e0-...",
  "transcript": "Someone is following me",
  "language": "en-IN",
  "threat_level": "HIGH",
  "events": ["Screams"],
  "is_safe": false,
  "incident_type": "Stalking",
  "reasons": "User describes being followed and expresses fear",
  "timestamp": "2026-05-30T14:37:15.000Z"
}
```

| Field | Type | Notes |
|-------|------|-------|
| `type` | string | always `"threat_update"` |
| `transcript` | string | what the user said, in the detected language |
| `language` | string | BCP-47 code: `en-IN`, `hi-IN`, `mr-IN`, … |
| `threat_level` | string | `LOW` / `MEDIUM` / `HIGH` / `CRITICAL` |
| `events` | string[] | e.g. `Screams`, `Aggression`, `Crying`, `Vehicle Crash`, `Heavy Breathing` |
| `is_safe` | bool | `true` when the user explicitly indicates safety → level resets to `LOW` |
| `incident_type` | string | `Stalking`, `Assault`, `Robbery`, `Accident`, `None`, … |
| `reasons` | string | AI explanation of the assessment |
| `timestamp` | string | ISO 8601 UTC |

> **Feature hook:** the app uses `threat_level` (+ `incident_type`/`reasons`) from this message to rewrite the recurring 20-second SOS SMS and encode the threat level. See the app-side spec `AI_THREAT_AWARE_SMS_FEATURE.md`.

### Lifecycle

```
1. POST /emergency/start        → session_id
2. POST /location/update        → first GPS (app then sends SOS SMS)
3. WS connect /ws/audio/{id}    → open
4. stream PCM chunks            → continuous
5. receive threat_update msgs   → app adapts the SMS + UI
6. WS disconnect
7. POST /emergency/end          → compiled incident summary
```

### Threat level colours (suggested UI)

| Level | Hex |
|-------|-----|
| LOW | `#3fb950` |
| MEDIUM | `#f0a030` |
| HIGH | `#f85149` |
| CRITICAL | `#ff4444` |

### De-escalation — safe phrases

If the user says any of these, `is_safe` becomes `true` and `threat_level` drops to `LOW`:
- **English:** "I am safe", "I'm okay", "false alarm", "police is here", "all clear"
- **Hindi:** "मैं सुरक्षित हूं", "सब ठीक है", "पुलिस आ गई"
- **Marathi:** "मी सुरक्षित आहे", "पोलीस आले"

---

## 6. AI Conversation

### POST /conversation/message

Text chat with the AI safety assistant (context-aware — uses the session's recent transcripts). Backed by Groq with the Gemini → mock fallback chain.

`Authorization: Bearer <token>`

**Request Body**
```json
{ "message": "Someone is following me. I'm alone on a dark street.", "language": "en-IN" }
```

`language` is optional (auto-detected / inferred from the session if omitted).

**Response — 200 OK**
```json
{
  "guidance": "Stay calm. Move towards a well-lit area with people. Do not go home directly.",
  "questions": ["Is the person approaching you?", "Are you near any open shops?"],
  "recommendations": ["Walk towards a crowded area or police station.", "Keep your primary contact on speed dial."]
}
```

The AI responds in the same language the user spoke.

---

## 7. Text-to-Speech (TTS)

### POST /tts/synthesize

Converts AI guidance text to speech (Sarvam `bulbul:v1`).

`Authorization: Bearer <token>`

**Request Body**
```json
{ "text": "Stay calm. Move towards a well-lit area.", "language": "en-IN" }
```

`text` max ~500 chars. `language` default `en-IN` (also `hi-IN`, `mr-IN`, …).

- **200 OK** — binary WAV (`Content-Type: audio/wav`).
- **204 No Content** — `SARVAM_API_KEY` not configured → app should fall back to Android native TTS.

| Language | Speaker |
|----------|---------|
| `en-IN`, `hi-IN`, `mr-IN`, `bn-IN` | `anushka` (female) |
| `ta-IN`, `te-IN`, `kn-IN`, `ml-IN` | `abhilash` (male) |

---

## 8. Notifications

Push notifications fire automatically from the WebSocket pipeline when the threat escalates to HIGH or CRITICAL. Delivery is currently logged to MongoDB (real FCM/Expo delivery is a future step).

### POST /notifications/register

`Authorization: Bearer <token>`
```json
{ "deviceToken": "ExponentPushToken[xxxx]", "deviceType": "android" }
```
→ `{ "success": true, "message": "Device token registered" }`

### POST /notifications/send

`Authorization: Bearer <token>`
```json
{ "title": "SOS ALERT", "body": "HIGH threat detected" }
```

### GET /notifications

Returns the authenticated user's notification history.

---

## 9. Health & Monitoring

### GET /health
```json
{ "status": "healthy", "database": "connected", "timestamp": "2026-05-30T14:00:00.000Z" }
```

### GET /metrics
```json
{ "cpu_usage_pct": 3.1, "memory_usage_mb": 142.0, "active_websocket_connections": 1 }
```

### GET /version
```json
{ "app_name": "Safe Steps AI Backend", "version": "2.1.0", "api_environment": "production" }
```

---

## 10. Error Responses

```json
{ "detail": "Human-readable error message" }
```

Validation errors (422) use FastAPI's standard list format.

| Status | Meaning |
|--------|---------|
| 400 | Bad request (e.g. duplicate phone) |
| 401 | Missing/invalid JWT |
| 404 | Resource not found (user, session) |
| 422 | Validation error |
| 429 | Upstream rate limit (Sarvam STT — handled internally) |
| 500 | Internal server error |

---

## 11. Fallback Agents (offline / low connectivity)

These were **kept** deliberately — they keep threat detection and AI guidance working when the primary cloud LLM (Groq) is slow, rate-limited, or unreachable.

| Layer | Primary | Fallback chain | File |
|-------|---------|----------------|------|
| **Threat classification** | Groq `llama-3.1-8b-instant` | → multilingual **keyword fusion** (`threat_fusion.py`) when Groq fails or no key | `services/ai_threat_service.py` |
| **AI guidance / conversation** | Groq | → **Google Gemini** (`google-genai`) → **mock** structured response | `services/ai_service.py` |
| **Voice activity detection** | Silero VAD (ONNX, local) | → energy-based RMS detection if the ONNX model is unavailable | `services/vad_service.py` |
| **TTS** | Sarvam `bulbul:v1` | → `204 No Content` so the app uses Android native TTS | `services/tts_service.py` |

The keyword-fusion engine recognises distress terms across English, Hindi, and Marathi (e.g. *bachao*, *vachva*) and also applies the GPS-speed override, so a meaningful `threat_level` is always returned even with no LLM connectivity.
