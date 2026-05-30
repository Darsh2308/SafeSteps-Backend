from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.utils.logger import Logger
import os

# Bind LangSmith settings so the SDK auto-initializes
if settings.LANGSMITH_TRACING.lower() == "true" and settings.LANGSMITH_API_KEY:
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
    os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
    os.environ["LANGSMITH_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
    Logger.info("LangSmith Tracing active.")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend Intelligence Layer for Safe Steps Emergency Orchestration",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import (
    auth_router, profile_router, contacts_router, permissions_router,
    emergency_router, location_router, reports_router, transcripts_router,
    timeline_router, calls_router, conversation_router, notifications_router,
    analytics_router, admin_router, tts_router, ws_audio,
)

app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(contacts_router)
app.include_router(permissions_router)
app.include_router(emergency_router)
app.include_router(location_router)
app.include_router(reports_router)
app.include_router(transcripts_router)
app.include_router(timeline_router)
app.include_router(calls_router)
app.include_router(conversation_router)
app.include_router(notifications_router)
app.include_router(analytics_router)
app.include_router(admin_router)
app.include_router(tts_router)
app.include_router(ws_audio.router)


@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Safe Steps AI V2 — MongoDB backend. Use /health or /docs.",
    }
