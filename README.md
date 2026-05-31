# SafeSteps AI Backend

**Intelligence layer for the SafeSteps emergency response Android app.**

SafeSteps turns a smartphone into an always-ready personal safety companion. When a user triggers SOS, the backend immediately orchestrates live location tracking, multilingual AI threat assessment over a voice audio stream, automated incident reporting, and push notifications to emergency contacts — all without any manual input from the person in distress.

---

## What this backend does

### Before this backend existed

The SafeSteps Android app was a standalone tool:
- SOS button sent a one-time SMS with a static location link.
- No real-time monitoring during the incident.
- No audio or speech understanding.
- No AI analysis — the app had no way to assess how serious the situation was.
- Incident history was a flat local list with no summary or severity.

### After integrating this backend

Every SOS session is now a fully observed, AI-driven operation:

| Capability | How |
|---|---|
| **Real-time threat assessment** | Live audio is streamed over WebSocket; Groq LLM classifies each speech segment as LOW / MEDIUM / HIGH / CRITICAL and returns structured reasons |
| **Multilingual voice understanding** | Sarvam AI transcribes audio in 10 Indian languages (English, Hindi, Marathi, Bengali, Tamil, Telugu, Kannada, Malayalam, Gujarati, Punjabi) — the user never has to switch modes |
| **AI safety guidance** | User can text the AI agent mid-emergency to get contextual safety instructions and triage questions |
| **Automated incident report** | When SOS ends, Groq generates a structured incident report: threat level, incident type, summary, timeline of actions, and recommendations |
| **Live location trail** | GPS coordinates are logged throughout the session; the app receives a Google Maps link to include in SOS SMS (sent via the device's own SIM) |
| **Persistent session history** | All incidents are stored in MongoDB with full timeline, transcripts, audio events, and AI-generated reports — searchable and auditable |
| **Push notifications** | If threat escalates (LOW → HIGH/CRITICAL), an alert fires to registered device tokens |
| **Analytics dashboard** | Aggregate incident stats, severity breakdown, monthly trends available to the app |

---

## AI services integrated

### 1. Groq — Real-time LLM inference

- **Model:** `llama-3.1-8b-instant`
- **Why Groq:** Sub-200 ms response time is critical when analyzing live audio during an emergency. Standard cloud LLMs are too slow for real-time use.
- **Used for:**
  - **Threat classification** (`ai_threat_service.py`) — receives the latest speech transcript, prior threat level, and recent conversation history; returns `threat_level`, `incident_type`, `is_safe`, and human-readable `reasons`.
  - **AI safety chat** (`ai_service.py`) — responds to user messages with structured `guidance`, follow-up `questions`, and `recommendations` in the user's language.
  - **Incident report generation** (`report_service.py`) — synthesizes the full session (transcripts + audio events + timeline) into a structured report with `summary`, `actions_taken`, and `recommendations`.
- **Observability:** All Groq calls are traced via LangSmith (optional, toggle via env var).
- **Fallback:** Google Gemini (`google-genai`) is used if Groq is unavailable.

### 2. Sarvam AI — Multilingual speech processing

- **STT model:** `saaras:v3` (fallback: `v1`)
- **TTS model:** `bulbul:v1`
- **Why Sarvam:** Only Indian-language-first STT/TTS provider with production-quality support for 10 regional languages including Marathi, Tamil, Telugu, Kannada, and others — critical for SafeSteps' primary Indian market.
- **Used for:**
  - **Speech-to-Text** (`stt_service.py`) — converts each audio segment into text, and auto-detects the language being spoken (returns a BCP-47 language code like `hi-IN`, `mr-IN`).
  - **Text-to-Speech** (`tts_service.py`) — converts AI guidance back to audio so the user can hear instructions hands-free. Speaker is selected per language (e.g., `anushka` for Hindi/Marathi, `abhilash` for South Indian languages).

### 3. Silero VAD — On-device voice activity detection

- **Runtime:** ONNX (via `onnxruntime`)
- **Why local:** VAD runs on every 0.5-second audio chunk. Using a cloud API for this would add unacceptable latency and cost. Running ONNX locally keeps it under 5 ms per chunk with zero network dependency.
- **Used for:** Deciding whether an audio chunk contains speech before sending it to Sarvam STT. This suppresses silent/noise chunks and prevents unnecessary API calls.
- **Fallback:** Energy-based RMS detection if the ONNX model file is unavailable.

### 4. LangSmith — LLM observability (optional)

- Wraps all Groq calls with `@traceable` so every threat analysis and report generation run is logged, searchable, and can be replayed for debugging.
- Disabled by default. Enabled by setting `LANGSMITH_TRACING=true` and providing a `LANGSMITH_API_KEY`.

---

## How the real-time pipeline works

```
Android app
    │
    ├── POST /emergency/start       → Creates session, returns session_id
    │
    ├── POST /location/update       → Appends GPS coords, returns Maps link for SMS
    │
    ├── WS  /ws/audio/{session_id}  → Streams raw 16kHz PCM audio
    │       │
    │       ├── Silero VAD          → Is this chunk speech?
    │       ├── Sarvam STT          → Transcribe → detected language
    │       ├── Groq LLM            → Threat level + reasons (with prior context)
    │       ├── Keyword fusion      → Multilingual keyword override (bachao, vachva…)
    │       ├── GPS speed override  → High speed + crash event → CRITICAL
    │       ├── Call state override → Failed call → escalate threat
    │       └── WebSocket response  → { threat_level, transcript, language, events }
    │
    ├── POST /conversation/message  → AI safety chat (Groq)
    │
    └── POST /emergency/end         → Closes session, triggers report generation (Groq)
                                      Returns full LoggedIncidentSchema
```

---

## API surface

| Domain | Endpoints |
|---|---|
| Auth | `POST /auth/register` `POST /auth/login` `POST /auth/logout` `GET /auth/me` |
| Profile | `GET/PUT /profile` `PUT /profile/language` `PUT /profile/sim` `GET/PUT /profile/settings` |
| Contacts | `GET/POST /contacts` `PUT/DELETE /contacts/{id}` |
| Emergency | `POST /emergency/start` `POST /emergency/end` `GET /emergency/current` `GET /emergency/incidents` `GET /emergency/{id}` |
| Location | `POST /location/update` `GET /location/{session_id}` `GET /location/history/{session_id}` |
| Timeline | `POST /timeline/event` `GET /timeline/{session_id}` |
| Transcripts | `POST /transcript` `GET /transcript/{session_id}` |
| Calls | `POST /call/status` `GET /call/{session_id}` |
| AI Chat | `POST /conversation/message` |
| TTS | `POST /tts/synthesize` |
| Reports | `POST /report/generate` `GET /report/{session_id}` |
| Notifications | `POST /notifications/register` `POST /notifications/send` `GET /notifications` |
| Analytics | `GET /analytics` `GET /analytics/incidents` `GET /analytics/severity` `GET /analytics/monthly` `GET /analytics/trends` |
| Monitoring | `GET|HEAD /health` `GET /metrics` `GET /version` |
| WebSocket | `WS /ws/audio/{session_id}` |

Full interactive docs available at `/docs` (Swagger UI) when the server is running.

---

## Tech stack

| Layer | Technology |
|---|---|
| Framework | FastAPI + Uvicorn |
| Database | MongoDB Atlas via Motor (async) + Beanie ODM |
| Auth | JWT (python-jose) — phone-number based, no OTP |
| AI / LLM | Groq (primary), Google Gemini (fallback) |
| Speech | Sarvam AI (STT + TTS) |
| VAD | Silero ONNX (local) |
| Observability | LangSmith (optional) |
| Deployment | Docker → Render.com |

---

## Running locally

```bash
# 1. Create and activate virtual environment
python -m venv venv && source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
cp .env.example .env   # fill in your keys

# 4. Start the server
python run.py
# → http://localhost:8000/docs
```

### Required environment variables

```
MONGODB_URL=mongodb+srv://<user>:<pass>@cluster.mongodb.net
MONGODB_DB_NAME=safesteps
SECRET_KEY=<random-secret>
GROQ_API_KEY=<groq-key>
SARVAM_API_KEY=<sarvam-key>

# Optional
GEMINI_API_KEY=
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
```

---

## Running tests

Tests use `mongomock-motor` for an in-memory MongoDB — no real database needed.

```bash
pytest tests/ -v
```

**20 tests across 4 files:**
- `test_ai.py` — VAD, STT, audio event detection, threat fusion engine, AI guidance + report generation
- `test_auth.py` — register, login, duplicate prevention, profile update, language/settings endpoints
- `test_emergency.py` — contact CRUD (max-3 limit), full session lifecycle (start → location → timeline → end), incident history, concurrent session handling
- `test_ws_audio.py` — WebSocket audio ingestion, invalid session rejection
