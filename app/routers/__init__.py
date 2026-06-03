from app.routers.auth import router as auth_router
from app.routers.emergency import router as emergency_router
from app.routers.location import router as location_router
from app.routers.conversation import router as conversation_router
from app.routers.notifications import router as notifications_router
from app.routers.admin import router as admin_router
from app.routers.tts import router as tts_router

__all__ = [
    "auth_router", "emergency_router", "location_router",
    "conversation_router", "notifications_router", "admin_router", "tts_router",
]
