# SafeSteps AI V2 — Backend API Documentation

**Version:** 2.0.0  
**Base URL (local dev):** `http://localhost:8000`  
**Base URL (production):** Set `EXPO_PUBLIC_API_BASE_URL` in the React Native app (`src/config/env.ts`)  
**Interactive Docs:** `http://localhost:8000/docs`

---

## Table of Contents

1. [Authentication & Headers](#1-authentication--headers)
2. [Auth Endpoints](#2-auth-endpoints)
3. [Profile](#3-profile)
4. [Emergency Contacts](#4-emergency-contacts)
5. [Permissions Sync](#5-permissions-sync)
6. [Emergency Session](#6-emergency-session)
7. [GPS Location](#7-gps-location)
8. [WebSocket — Live Audio](#8-websocket--live-audio)
9. [AI Conversation](#9-ai-conversation)
10. [Text-to-Speech (TTS)](#10-text-to-speech-tts)
11. [Call Status](#11-call-status)
12. [Reports](#12-reports)
13. [Timeline](#13-timeline)
14. [Transcripts](#14-transcripts)
15. [Notifications](#15-notifications)
16. [Analytics](#16-analytics)
17. [Health & Monitoring](#17-health--monitoring)
18. [Error Responses](#18-error-responses)
19. [App Integration Map](#19-app-integration-map)
20. [TypeScript Types for the App](#20-typescript-types-for-the-app)

---

## 1. Authentication & Headers

### How Authentication Works

Every protected endpoint requires a **JWT Bearer token** in the `Authorization` header.

```
Authorization: Bearer <token>
```

The token is returned on **register** or **login** and never expires in dev (8-day expiry in production). The React Native app's `apiClient.ts` already handles this automatically via the request interceptor — it reads the token from `storageService` and attaches it.

### Storing the Token (React Native)

```typescript
// After register or login — save the token
await storageService.setItem('authToken', response.token);

// The apiClient.ts interceptor reads it automatically on every request
// No manual header management needed
```

### Unauthenticated Endpoints

These endpoints do **not** require a token:
- `POST /auth/register`
- `POST /auth/login`
- `GET /health`
- `GET /metrics`
- `GET /version`
- `WS /ws/audio/{session_id}`

---

## 2. Auth Endpoints

> **App file to update:** `src/services/apiServices.ts` → `authService`  
> **App screen:** `src/screens/setup/PhoneVerificationScreen.tsx`

### ⚠️ Breaking Change from Previous Version

The old OTP flow (`/auth/send-otp`, `/auth/verify-otp`) has been **removed**. Replace with register + login below.

---

### POST /auth/register

Creates a new user account. Phone number is the unique identity — no password.

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

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `phone` | string | ✅ | Must be unique. Use E.164 format: `+91XXXXXXXXXX` |
| `full_name` | string | ✅ | — |
| `age` | string | ❌ | — |
| `date_of_birth` | string | ❌ | — |
| `gender` | string | ❌ | — |
| `blood_group` | string | ❌ | — |
| `medical_notes` | string | ❌ | — |
| `preferred_language` | string | ❌ | Default: `"English"` |

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

**Error Responses**

| Status | Condition | Message |
|--------|-----------|---------|
| 400 | Phone already registered | `"This phone number is already registered. Please log in instead."` |

---

### POST /auth/login

Login with a registered phone number. No password required.

**Request Body**
```json
{
  "phone": "+919999999999"
}
```

**Response — 200 OK**  
Same as register response (`TokenResponse` with token + user profile).

**Error Responses**

| Status | Condition | Message |
|--------|-----------|---------|
| 404 | Phone not registered | `"Phone number not registered. Please register first."` |

---

### POST /auth/logout

Invalidates the session. The client must discard the stored JWT token.

**Headers:** `Authorization: Bearer <token>`  
**Request Body:** None

**Response — 200 OK**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

### GET /auth/me

Returns the authenticated user's full profile.

**Headers:** `Authorization: Bearer <token>`

**Response — 200 OK**  
Returns `ProfileSchema` (same as the `user` object in `TokenResponse`).

---

## 3. Profile

> **App file:** `src/services/apiServices.ts` → `profileService`  
> **App screen:** `src/screens/dashboard/ProfileScreen.tsx`

### GET /profile

**Headers:** `Authorization: Bearer <token>`

**Response — 200 OK**
```json
{
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
```

---

### PUT /profile

Update any profile fields. All fields are optional — only send what changed.

**Headers:** `Authorization: Bearer <token>`

**Request Body** (all fields optional)
```json
{
  "fullName": "Darsh Patil",
  "age": "25",
  "gender": "Male",
  "bloodGroup": "O+",
  "medicalNotes": "",
  "preferredLanguage": "Hindi",
  "notificationEnabled": true,
  "privacyEnabled": false,
  "themeDarkMode": true,
  "sosSensitivity": 0.7
}
```

**Response — 200 OK**  
Returns updated `ProfileSchema`.

---

### PUT /profile/language

Quick update for preferred language only.

**Request Body**
```json
{ "language": "hi-IN" }
```

---

### GET/PUT /profile/settings

Get or update notification, privacy, theme, and SOS sensitivity settings.

**PUT Request Body**
```json
{
  "notificationEnabled": true,
  "privacyEnabled": true,
  "themeDarkMode": false,
  "sosSensitivity": 0.6
}
```

---

## 4. Emergency Contacts

> **App file:** `src/services/apiServices.ts` → `contactService`  
> **App screen:** `src/screens/dashboard/ContactsScreen.tsx`, `src/screens/setup/ContactsSetupScreen.tsx`  
> **App component:** `src/components/AddContactModal.tsx`

**Maximum 3 contacts per user.** Priority determines who gets called vs SMS'd only.

| Priority | Behavior |
|----------|----------|
| `"Primary"` | Gets SMS with Maps link + phone call |
| `"Secondary"` | Gets SMS with Maps link only |
| `"Tertiary"` | Gets SMS with Maps link only |

### POST /contacts

**Headers:** `Authorization: Bearer <token>`

**Request Body**
```json
{
  "name": "Mom",
  "relationship": "Mother",
  "phoneNumber": "+919888888888",
  "priority": "Primary"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | ✅ | — |
| `relationship` | string | ✅ | e.g., Mother, Father, Friend |
| `phoneNumber` | string | ✅ | E.164 format |
| `priority` | string | ✅ | `"Primary"` / `"Secondary"` / `"Tertiary"` |

**Response — 201 Created**
```json
{
  "id": "a1b2c3d4-...",
  "name": "Mom",
  "relationship": "Mother",
  "phoneNumber": "+919888888888",
  "priority": "Primary"
}
```

**Error Responses**

| Status | Condition |
|--------|-----------|
| 400 | Already have 3 contacts |

---

### GET /contacts

Returns all contacts for the authenticated user, sorted by priority.

**Response — 200 OK**
```json
[
  {
    "id": "a1b2c3d4-...",
    "name": "Mom",
    "relationship": "Mother",
    "phoneNumber": "+919888888888",
    "priority": "Primary"
  }
]
```

---

### PUT /contacts/{contact_id}

Update an existing contact. Same request body as POST.

---

### DELETE /contacts/{contact_id}

**Response — 200 OK**
```json
{ "success": true }
```

---

## 5. Permissions Sync

> **App file:** `src/services/permissionService.ts`  
> **App screen:** `src/screens/setup/PermissionsScreen.tsx`

Sync the device's runtime permission status to the backend. Call this once at app startup and again whenever permissions change.

### POST /permissions/sync

**Headers:** `Authorization: Bearer <token>`

**Request Body**
```json
{
  "permissions": [
    { "name": "Location Access",       "description": "GPS coordinates during emergency.", "type": "location",      "status": true  },
    { "name": "Microphone Usage",      "description": "Background audio and transcription.", "type": "microphone",  "status": true  },
    { "name": "Send SMS",              "description": "Alert texts to contacts.",           "type": "sms",          "status": true  },
    { "name": "Phone Calls",           "description": "Dial primary contacts.",             "type": "phone",        "status": true  },
    { "name": "Access Contacts",       "description": "Import contacts from device.",       "type": "contacts",     "status": true  },
    { "name": "Notifications",         "description": "Critical alert statuses.",           "type": "notifications","status": true  },
    { "name": "Accessibility Service", "description": "Hardware trigger intercepts.",       "type": "accessibility","status": false }
  ]
}
```

`status: true` = granted, `status: false` = denied.

**Response — 200 OK**
```json
{ "success": true, "message": "Permissions synced" }
```

---

### GET /permissions

Returns cached permission state (defaults to all false if never synced).

---

## 6. Emergency Session

> **App file:** `src/services/apiServices.ts` → `emergencyService`  
> **App component:** `src/components/SOSButton.tsx`, `src/hooks/useSosHold.ts`

This is the core SOS flow. Start → Location → Audio Stream → End.

### POST /emergency/start

Starts a new SOS session. If a session is already active, it is closed first.

**Headers:** `Authorization: Bearer <token>`  
**Request Body:** None

**Response — 200 OK**
```json
{
  "session_id": "cfc004e0-3c52-40dd-8ddc-dffd696b4ab9",
  "tracking_id": "8b3f2a1c-...",
  "created_at": "2026-05-30T14:35:22.000Z"
}
```

> **Store `session_id`** — needed for WebSocket, location updates, reports, and timeline.

---

### POST /emergency/end

Ends the active session. Automatically:
1. Generates AI incident report

> **Safe SMS** is sent by the app via Android SmsManager after receiving this response — not by the backend.

**Headers:** `Authorization: Bearer <token>`  
**Request Body:** None

**Response — 200 OK**  
Returns `LoggedIncidentSchema` (full session summary with report).

```json
{
  "id": "cfc004e0-...",
  "date": "2026-05-30",
  "startTime": "14:35:22",
  "endTime": "14:47:10",
  "duration": "11m 48s",
  "severity": "HIGH",
  "incidentType": "Stalking",
  "summary": "User reported being followed while walking alone...",
  "actionsPerformed": ["SOS Triggered", "SMS sent to 1 contact", "Live GPS tracking enabled"],
  "recommendations": ["Vary your route home", "Share location with trusted contact"],
  "timeline": [...],
  "transcript": [...]
}
```

---

### GET /emergency/current

Returns the currently active session, or `null` if none.

**Response — 200 OK**
```json
{
  "session_id": "cfc004e0-...",
  "tracking_id": "8b3f2a1c-...",
  "created_at": "2026-05-30T14:35:22.000Z"
}
```
or `null`

---

### GET /emergency/history

Returns all past sessions for the authenticated user, sorted newest first.

**Response — 200 OK**  
Array of `LoggedIncidentSchema`.

---

## 7. GPS Location

> **App integration:** Call after SOS starts, then every 30 seconds while session is active.

### POST /location/update

**Headers:** `Authorization: Bearer <token>`

**Request Body**
```json
{
  "latitude": 19.0760,
  "longitude": 72.8777,
  "accuracy": 5.0,
  "speed": 0.0,
  "heading": 0.0
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `latitude` | float | ✅ | — |
| `longitude` | float | ✅ | — |
| `accuracy` | float | ❌ | Meters. Default 0.0 |
| `speed` | float | ❌ | **m/s** (not km/h). Default 0.0 |
| `heading` | float | ❌ | Degrees 0–360. Default 0.0 |

> **Important:** `speed` is in **m/s**. Convert from km/h: `speed_ms = speed_kmh / 3.6`  
> Speeds > 80 km/h (22.2 m/s) escalate threat to MEDIUM via the Threat Fusion Engine.

**Response — 200 OK**
```json
{
  "success": true,
  "maps_link": "https://maps.google.com/?q=19.076,72.8777",
  "is_first_update": true
}
```

> **`is_first_update: true`** means this is the first GPS fix of the session.  
> When you receive this, **send the SOS SMS from the app** using Android SmsManager with `maps_link`.  
> Subsequent updates (`is_first_update: false`) only track movement — no SMS needed unless you want periodic location updates.

---

### GET /location/{session_id}

Returns the latest GPS location for a session.

---

### GET /location/history/{session_id}

Returns all recorded locations for a session (full movement trail).

---

## 8. WebSocket — Live Audio

> **App integration:** Connect after `POST /emergency/start`. Stream microphone audio continuously.

### WS /ws/audio/{session_id}

**No auth header required** (session_id is the auth).  
**Protocol:** Binary WebSocket  
**Audio format:** Raw PCM, 16kHz, 16-bit signed, Mono

**Connection URL:**
```
ws://localhost:8000/ws/audio/{session_id}
ws://your-production-domain/ws/audio/{session_id}
```

---

### Sending Audio (Client → Server)

Send raw PCM audio bytes as binary WebSocket messages. Convert Float32 microphone data to Int16 before sending:

```typescript
// React Native (using expo-av or react-native-audio-recorder-player)
// Record at: sampleRate=16000, channels=1, bitsPerSample=16
// Send binary chunks continuously

webSocket.send(int16ArrayBuffer);
```

**Recommended chunk size:** 4096 samples (256ms at 16kHz)  
The backend accumulates speech and fires STT every ~3 seconds (rate-limit cooldown).

---

### Receiving Messages (Server → Client)

The server pushes a JSON message after every STT + AI analysis cycle:

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
| `type` | string | Always `"threat_update"` |
| `transcript` | string | What the user said (in detected language) |
| `language` | string | BCP-47 code: `en-IN`, `hi-IN`, `mr-IN` |
| `threat_level` | string | `LOW` / `MEDIUM` / `HIGH` / `CRITICAL` |
| `events` | string[] | Detected events: `Screams`, `Aggression`, `Crying`, `Vehicle Crash`, `Heavy Breathing` |
| `is_safe` | bool | `true` if user explicitly said "I am safe" etc. |
| `incident_type` | string | `Stalking`, `Assault`, `Robbery`, `Accident`, `Medical Emergency`, `None`, etc. |
| `reasons` | string | AI explanation for the threat assessment |
| `timestamp` | string | ISO 8601 UTC |

---

### WebSocket Lifecycle

```
1. POST /emergency/start          → get session_id
2. POST /location/update          → first GPS (triggers SOS SMS)
3. WS connect /ws/audio/{id}      → open connection
4. Send PCM audio chunks          → continuous stream
5. Receive threat_update messages → update UI in real time
6. WS disconnect                  → stop streaming
7. POST /emergency/end            → generates report + safe SMS
```

---

### Threat Level Display

Use these colors in the app UI:

| Level | Color | Hex |
|-------|-------|-----|
| `LOW` | Green | `#3fb950` |
| `MEDIUM` | Amber | `#f0a030` |
| `HIGH` | Red | `#f85149` |
| `CRITICAL` | Bright Red | `#ff4444` |

---

### De-escalation — Safe Phrases

If the user says any of these, `is_safe` will be `true` and `threat_level` will drop to `LOW`:

- **English:** "I am safe", "I'm okay", "false alarm", "police is here", "all clear"
- **Hindi:** "मैं सुरक्षित हूं", "सब ठीक है", "पुलिस आ गई"
- **Marathi:** "मी सुरक्षित आहे", "पोलीस आले"

---

## 9. AI Conversation

> **App integration:** Active during an SOS session when the contact does not answer (Scenario 3 in workflow).

### POST /conversation/message

Sends a message to the AI safety assistant. Context-aware — uses last 10 exchanges.

**Headers:** `Authorization: Bearer <token>`

**Request Body**
```json
{
  "message": "Someone is following me. I'm alone on a dark street.",
  "language": "en-IN"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `message` | string | ✅ | The user's text or speech-to-text result |
| `language` | string | ❌ | BCP-47 code. AI detects automatically if omitted |

**Response — 200 OK**
```json
{
  "guidance": "Stay calm. Move towards a well-lit area with people. Do not go home directly.",
  "questions": [
    "Is the person keeping their distance or approaching you?",
    "Are you near any open shops or buildings?"
  ],
  "recommendations": [
    "Walk towards a crowded area or police station.",
    "Keep your primary contact on speed dial."
  ]
}
```

> The AI responds **in the same language** the user spoke in (`language` field).

---

## 10. Text-to-Speech (TTS)

> **App integration:** Play this audio after receiving AI guidance. Fall back to Android Native TTS if this returns 204.

### POST /tts/synthesize

Converts AI response text to speech audio.

**Headers:** `Authorization: Bearer <token>`

**Request Body**
```json
{
  "text": "Stay calm. Move towards a well-lit area.",
  "language": "en-IN"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `text` | string | ✅ | Max 500 characters |
| `language` | string | ❌ | Default: `"en-IN"`. Also supports `hi-IN`, `mr-IN` |

**Response — 200 OK**  
Binary WAV audio bytes (`Content-Type: audio/wav`).

**Response — 204 No Content**  
Returned when `SARVAM_API_KEY` is not set in `.env`.  
**App should fall back to Android Native TTS** when it receives 204.

**Voices Used:**
| Language | Speaker |
|----------|---------|
| `en-IN`, `hi-IN`, `mr-IN`, `bn-IN` | `anushka` (female) |
| `ta-IN`, `te-IN`, `kn-IN`, `ml-IN` | `abhilash` (male) |

---

## 11. Call Status

> **App integration:** Log every call attempt to the primary contact from Android Telecom APIs.

### POST /call/status

Logs the current state of the emergency call. Used by the Threat Fusion Engine to escalate if calls fail.

**Headers:** `Authorization: Bearer <token>`

**Request Body**
```json
{
  "state": "Answered"
}
```

| `state` value | When to send |
|---------------|-------------|
| `"Initiated"` | When the call is placed |
| `"Ringing"` | When the remote phone starts ringing |
| `"Answered"` | When the contact picks up |
| `"Ended"` | When the call ends normally |
| `"Failed"` | When no one answered / call dropped |

**Response — 200 OK**
```json
{ "success": true, "message": "Call status updated" }
```

> **Threat escalation:** If `"Failed"` appears in the last 5 call logs and threat level is currently LOW, it escalates to MEDIUM automatically.

---

### GET /call/{session_id}

**Response — 200 OK**
```json
{
  "state": "Answered",
  "history": [
    { "state": "Initiated", "timestamp": "2026-05-30T14:35:25.000Z" },
    { "state": "Ringing",   "timestamp": "2026-05-30T14:35:27.000Z" },
    { "state": "Answered",  "timestamp": "2026-05-30T14:35:31.000Z" }
  ]
}
```

---

## 12. Reports

> **App screen:** `src/screens/dashboard/IncidentDetailsScreen.tsx`

Reports are **auto-generated** when `POST /emergency/end` is called. No manual trigger needed.

### GET /reports/{session_id}

**Headers:** `Authorization: Bearer <token>`

**Response — 200 OK**
```json
{
  "threatLevel": "HIGH",
  "incidentType": "Stalking",
  "summary": "User was followed by an unknown individual for approximately 10 minutes while walking alone at night near a residential area.",
  "actionsTaken": [
    "SOS session activated",
    "GPS tracking enabled",
    "SMS with location sent to 1 contact"
  ],
  "recommendations": [
    "Vary your route home regularly.",
    "Share your live location with trusted contacts during late-night travel.",
    "Report the incident to the nearest police station."
  ]
}
```

---

## 13. Timeline

> **App screen:** `src/screens/dashboard/IncidentDetailsScreen.tsx`

### GET /timeline/{session_id}

Returns chronological event log for a session.

**Response — 200 OK**
```json
[
  { "time": "14:35:22", "event": "SOS session started" },
  { "time": "14:35:30", "event": "GPS location acquired" },
  { "time": "14:35:31", "event": "SOS SMS sent to Mom (+919888888888)" },
  { "time": "14:36:05", "event": "Threat Level → HIGH" },
  { "time": "14:37:12", "event": "Audio Event: Screams (AI-detected)" },
  { "time": "14:47:10", "event": "User confirmed safety — session de-escalated." }
]
```

---

### POST /timeline/event

Manually add a timeline event (e.g., from the Android app when a hardware SOS button is pressed).

**Request Body**
```json
{ "event": "Volume button SOS triggered by user" }
```

---

## 14. Transcripts

### GET /transcripts/{session_id}

Returns all speech transcripts for a session.

**Response — 200 OK**
```json
[
  {
    "time": "14:36:05",
    "speaker": "User",
    "text": "Someone is following me",
    "language": "en-IN",
    "confidence": 0.94
  },
  {
    "time": "14:37:12",
    "speaker": "User",
    "text": "Please help me",
    "language": "en-IN",
    "confidence": 0.91
  }
]
```

---

## 15. Notifications

### POST /notifications/register

Register device push token after login. Call once after app startup.

**Headers:** `Authorization: Bearer <token>`

**Request Body**
```json
{
  "deviceToken": "ExponentPushToken[xxxx]",
  "deviceType": "android"
}
```

**Response — 201 Created**
```json
{ "success": true, "message": "Device token registered" }
```

> **Note:** Push notification delivery is currently logged to MongoDB only. Real FCM/Expo delivery is a v2 feature.

---

### GET /notifications

Returns notification history for the authenticated user.

**Response — 200 OK**
```json
[
  {
    "id": "...",
    "title": "SOS ALERT: HIGH Threat Detected",
    "body": "User describes being followed and expresses fear",
    "sent_at": "2026-05-30T14:36:05.000Z",
    "status": "success"
  }
]
```

---

## 16. Analytics

> **App screen:** `src/screens/dashboard/AnalyticsScreen.tsx`

### GET /analytics

**Headers:** `Authorization: Bearer <token>`

**Response — 200 OK**
```json
{
  "totalEncounters": 12,
  "avgResponseLimit": "4m 22s",
  "criticalCount": 2,
  "highCount": 5,
  "mediumCount": 3,
  "lowCount": 2
}
```

---

### GET /analytics/incidents

Breakdown by incident type.

```json
[
  { "type": "Stalking",  "count": 4 },
  { "type": "Assault",   "count": 2 },
  { "type": "Unknown",   "count": 6 }
]
```

---

### GET /analytics/severity

```json
{
  "CRITICAL": 2,
  "HIGH": 5,
  "MEDIUM": 3,
  "LOW": 2
}
```

---

### GET /analytics/monthly

Last 180 days, grouped by month.

```json
[
  { "month": "2026-05", "count": 3 },
  { "month": "2026-04", "count": 2 }
]
```

---

## 17. Health & Monitoring

### GET /health

```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2026-05-30T14:00:00.000Z"
}
```

### GET /version

```json
{
  "app_name": "Safe Steps AI Backend",
  "version": "2.0.0",
  "api_environment": "production"
}
```

---

## 18. Error Responses

All errors follow this format:

```json
{
  "detail": "Human-readable error message"
}
```

Or for validation errors (422):

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "phone"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

| HTTP Status | Meaning |
|-------------|---------|
| 400 | Bad request (duplicate phone, max contacts exceeded) |
| 401 | Missing or invalid JWT token |
| 404 | Resource not found (user, session, contact) |
| 422 | Validation error — wrong field names or types |
| 429 | Rate limit exceeded (Sarvam STT — handled internally) |
| 500 | Internal server error |

---

## 19. App Integration Map

This table shows which screen/file in the React Native app connects to which API endpoint, and what needs updating.

| Screen / File | Current State | API to Call | Action Required |
|---------------|---------------|-------------|-----------------|
| `PhoneVerificationScreen.tsx` | Calls `/auth/send-otp` + `/auth/verify-otp` | `POST /auth/register` + `POST /auth/login` | **Update** `authService` in `apiServices.ts` |
| `ProfileSetupScreen.tsx` | — | `POST /auth/register` (pass all fields here) | Integrate on form submit |
| `ProfileScreen.tsx` | Calls `profileService.getProfile()` | `GET /profile` | ✅ Already wired (check field names) |
| `ContactsSetupScreen.tsx` + `ContactsScreen.tsx` | Calls `contactService.addContact()` | `POST /contacts` | **Fix field:** `phoneNumber` (camelCase), `priority` as string |
| `PermissionsScreen.tsx` | Uses `permissionService.ts` | `POST /permissions/sync` | **Update** to send `permissions[]` array format |
| `SOSButton.tsx` / `useSosHold.ts` | Calls `/emergency/trigger` | `POST /emergency/start` → `POST /location/update` → `WS connect` | **Update** to 3-step SOS start flow |
| HomeScreen GPS loop | — | `POST /location/update` every 30s | **Add** background location interval |
| Audio streaming | Not implemented | `WS /ws/audio/{session_id}` | **Implement** WebSocket + PCM audio pipeline |
| AI Conversation | Not implemented | `POST /conversation/message` | **Implement** when call not answered |
| TTS playback | Not implemented | `POST /tts/synthesize` → play WAV | **Implement** with Android MediaPlayer fallback |
| Call logging | Not implemented | `POST /call/status` | **Implement** via Android Telecom callback |
| `IncidentDetailsScreen.tsx` | Calls `getIncidents()` | `GET /emergency/history` + `GET /reports/{id}` + `GET /timeline/{id}` | Update endpoint names |
| `AnalyticsScreen.tsx` | Calls `analyticsService.getAnalytics()` | `GET /analytics` | ✅ Already wired |
| Push token | Not implemented | `POST /notifications/register` | **Add** after login |

---

## 20. TypeScript Types for the App

Replace or update `src/types/models.ts` with these types to match the current backend exactly.

```typescript
// ── Auth ──────────────────────────────────────────────────────────────────────

export interface RegisterRequest {
  phone: string;
  full_name: string;
  age?: string;
  date_of_birth?: string;
  gender?: string;
  blood_group?: string;
  medical_notes?: string;
  preferred_language?: string;
}

export interface LoginRequest {
  phone: string;
}

export interface TokenResponse {
  success: boolean;
  token: string;
  user: ProfileState;
}

// ── Profile ───────────────────────────────────────────────────────────────────

export interface ProfileState {
  fullName: string;
  age: string;
  dateOfBirth: string;
  gender: string;
  bloodGroup: string;
  medicalNotes: string;
  phone: string;
  preferredLanguage: string;
  notificationEnabled: boolean;
  privacyEnabled: boolean;
  themeDarkMode: boolean;
  sosSensitivity: number;
}

// ── Contacts ──────────────────────────────────────────────────────────────────

export type ContactPriority = 'Primary' | 'Secondary' | 'Tertiary';

export interface Contact {
  id: string;
  name: string;
  relationship: string;
  phoneNumber: string;        // camelCase — matches backend alias
  priority: ContactPriority;
}

export type ContactCreate = Omit<Contact, 'id'>;

// ── Emergency Session ─────────────────────────────────────────────────────────

export interface EmergencySessionStart {
  session_id: string;
  tracking_id: string;
  created_at: string;
}

export interface LocationUpdate {
  latitude: number;
  longitude: number;
  accuracy?: number;
  speed?: number;   // m/s — divide km/h by 3.6
  heading?: number;
}

// ── WebSocket ─────────────────────────────────────────────────────────────────

export type ThreatLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type AudioEvent = 'Screams' | 'Aggression' | 'Crying' | 'Vehicle Crash' | 'Heavy Breathing';
export type IncidentType =
  | 'Stalking' | 'Assault' | 'Robbery' | 'Harassment'
  | 'Accident' | 'Medical Emergency' | 'Unknown' | 'None';

export interface ThreatUpdate {
  type: 'threat_update';
  session_id: string;
  transcript: string;
  language: string;
  threat_level: ThreatLevel;
  events: AudioEvent[];
  is_safe: boolean;
  incident_type: IncidentType;
  reasons: string;
  timestamp: string;
}

// ── Conversation ──────────────────────────────────────────────────────────────

export interface ConversationMessage {
  message: string;
  language?: string;
}

export interface ConversationResponse {
  guidance: string;
  questions: string[];
  recommendations: string[];
}

// ── Call Status ───────────────────────────────────────────────────────────────

export type CallState = 'Initiated' | 'Ringing' | 'Answered' | 'Ended' | 'Failed';

export interface CallStatusUpdate {
  state: CallState;
}

// ── Report ────────────────────────────────────────────────────────────────────

export interface IncidentReport {
  threatLevel: ThreatLevel;
  incidentType: IncidentType;
  summary: string;
  actionsTaken: string[];
  recommendations: string[];
}

// ── Timeline & Transcript ─────────────────────────────────────────────────────

export interface TimelineEvent {
  time: string;
  event: string;
}

export interface TranscriptEvent {
  time: string;
  speaker: string;
  text: string;
  language?: string;
  confidence?: number;
}

// ── Logged Incident (history) ─────────────────────────────────────────────────

export interface LoggedIncident {
  id: string;
  date: string;
  startTime: string;
  endTime: string;
  duration: string;
  severity: ThreatLevel;
  incidentType: IncidentType;
  summary: string;
  actionsPerformed: string[];
  recommendations: string[];
  timeline: TimelineEvent[];
  transcript: TranscriptEvent[];
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export interface Analytics {
  totalEncounters: number;
  avgResponseLimit: string;
  criticalCount: number;
  highCount: number;
  mediumCount: number;
  lowCount: number;
}

// ── Permissions ───────────────────────────────────────────────────────────────

export interface PermissionInfo {
  name: string;
  description: string;
  type: string;
  status: boolean;
}

export interface PermissionSyncRequest {
  permissions: PermissionInfo[];
}

// ── Notifications ─────────────────────────────────────────────────────────────

export interface NotificationRegister {
  deviceToken: string;
  deviceType: 'android' | 'ios';
}
```

---

## Updated apiServices.ts

Replace `src/services/apiServices.ts` with this to match the current backend:

```typescript
import { apiClient } from '../api/apiClient';
import {
  RegisterRequest, LoginRequest, TokenResponse,
  ProfileState, Contact, ContactCreate,
  EmergencySessionStart, LocationUpdate, LoggedIncident,
  ConversationMessage, ConversationResponse,
  CallStatusUpdate, IncidentReport,
  TimelineEvent, TranscriptEvent,
  Analytics, PermissionSyncRequest, NotificationRegister,
} from '../types/models';

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authService = {
  register: async (payload: RegisterRequest): Promise<TokenResponse> => {
    const res = await apiClient.post('/auth/register', payload);
    return res.data;
  },
  login: async (phone: string): Promise<TokenResponse> => {
    const res = await apiClient.post('/auth/login', { phone });
    return res.data;
  },
  logout: async (): Promise<void> => {
    await apiClient.post('/auth/logout');
  },
  getMe: async (): Promise<ProfileState> => {
    const res = await apiClient.get('/auth/me');
    return res.data;
  },
};

// ── Profile ───────────────────────────────────────────────────────────────────
export const profileService = {
  getProfile: async (): Promise<ProfileState> => {
    const res = await apiClient.get('/profile');
    return res.data;
  },
  updateProfile: async (profile: Partial<ProfileState>): Promise<ProfileState> => {
    const res = await apiClient.put('/profile', profile);
    return res.data;
  },
};

// ── Contacts ──────────────────────────────────────────────────────────────────
export const contactService = {
  getContacts: async (): Promise<Contact[]> => {
    const res = await apiClient.get('/contacts');
    return res.data;
  },
  addContact: async (contact: ContactCreate): Promise<Contact> => {
    const res = await apiClient.post('/contacts', contact);
    return res.data;
  },
  updateContact: async (id: string, contact: ContactCreate): Promise<Contact> => {
    const res = await apiClient.put(`/contacts/${id}`, contact);
    return res.data;
  },
  deleteContact: async (id: string): Promise<void> => {
    await apiClient.delete(`/contacts/${id}`);
  },
};

// ── Permissions ───────────────────────────────────────────────────────────────
export const permissionsService = {
  sync: async (payload: PermissionSyncRequest): Promise<void> => {
    await apiClient.post('/permissions/sync', payload);
  },
};

// ── Emergency ─────────────────────────────────────────────────────────────────
export const emergencyService = {
  start: async (): Promise<EmergencySessionStart> => {
    const res = await apiClient.post('/emergency/start');
    return res.data;
  },
  end: async (): Promise<LoggedIncident> => {
    const res = await apiClient.post('/emergency/end');
    return res.data;
  },
  getCurrent: async (): Promise<EmergencySessionStart | null> => {
    const res = await apiClient.get('/emergency/current');
    return res.data;
  },
  getHistory: async (): Promise<LoggedIncident[]> => {
    const res = await apiClient.get('/emergency/history');
    return res.data;
  },
};

// ── Location ──────────────────────────────────────────────────────────────────
export const locationService = {
  update: async (payload: LocationUpdate): Promise<{ success: boolean; maps_link: string }> => {
    const res = await apiClient.post('/location/update', payload);
    return res.data;
  },
};

// ── Call Status ───────────────────────────────────────────────────────────────
export const callService = {
  logStatus: async (state: CallStatusUpdate['state']): Promise<void> => {
    await apiClient.post('/call/status', { state });
  },
};

// ── Conversation ──────────────────────────────────────────────────────────────
export const conversationService = {
  sendMessage: async (payload: ConversationMessage): Promise<ConversationResponse> => {
    const res = await apiClient.post('/conversation/message', payload);
    return res.data;
  },
};

// ── Reports ───────────────────────────────────────────────────────────────────
export const reportService = {
  getReport: async (sessionId: string): Promise<IncidentReport> => {
    const res = await apiClient.get(`/reports/${sessionId}`);
    return res.data;
  },
  getTimeline: async (sessionId: string): Promise<TimelineEvent[]> => {
    const res = await apiClient.get(`/timeline/${sessionId}`);
    return res.data;
  },
  getTranscripts: async (sessionId: string): Promise<TranscriptEvent[]> => {
    const res = await apiClient.get(`/transcripts/${sessionId}`);
    return res.data;
  },
};

// ── Analytics ─────────────────────────────────────────────────────────────────
export const analyticsService = {
  getAnalytics: async (): Promise<Analytics> => {
    const res = await apiClient.get('/analytics');
    return res.data;
  },
};

// ── Notifications ─────────────────────────────────────────────────────────────
export const notificationService = {
  registerDevice: async (payload: NotificationRegister): Promise<void> => {
    await apiClient.post('/notifications/register', payload);
  },
};
```
