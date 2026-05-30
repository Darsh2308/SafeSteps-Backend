import motor.motor_asyncio
from beanie import init_beanie
from app.config import settings
from app.utils.logger import Logger


def get_motor_client() -> motor.motor_asyncio.AsyncIOMotorClient:
    return motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URL)


async def init_db() -> None:
    """Initialize Beanie with all document models. Call this once at app startup."""
    from app.models.user import User
    from app.models.contact import EmergencyContact
    from app.models.session import EmergencySession
    from app.models.notification import Notification

    client = get_motor_client()
    db = client[settings.MONGODB_DB_NAME]

    await init_beanie(
        database=db,
        document_models=[User, EmergencyContact, EmergencySession, Notification],
    )
    Logger.info(f"MongoDB connected → database: '{settings.MONGODB_DB_NAME}'")
