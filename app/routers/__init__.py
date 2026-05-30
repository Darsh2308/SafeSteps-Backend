from app.routers.auth import router as auth_router
from app.routers.profile import router as profile_router
from app.routers.contacts import router as contacts_router
from app.routers.permissions import router as permissions_router
from app.routers.emergency import router as emergency_router
from app.routers.location import router as location_router
from app.routers.reports import router as reports_router
from app.routers.transcripts import router as transcripts_router
from app.routers.timeline import router as timeline_router
from app.routers.calls import router as calls_router
from app.routers.conversation import router as conversation_router
from app.routers.notifications import router as notifications_router
from app.routers.analytics import router as analytics_router
from app.routers.admin import router as admin_router
from app.routers.tts import router as tts_router

__all__ = [
    "auth_router", "profile_router", "contacts_router", "permissions_router",
    "emergency_router", "location_router", "reports_router", "transcripts_router",
    "timeline_router", "calls_router", "conversation_router", "notifications_router",
    "analytics_router", "admin_router", "tts_router",
]
