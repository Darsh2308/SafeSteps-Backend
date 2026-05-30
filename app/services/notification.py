from app.models.notification import Notification
from app.utils.logger import Logger
from datetime import datetime


class NotificationService:
    async def send_push_notification(self, user_id: str, title: str, body: str) -> bool:
        """
        Logs push notification to MongoDB.
        Real delivery (FCM/Expo) requires device tokens — wire in send_real_push() below.
        """
        Logger.info(f"Push → user {user_id}: {title}")
        try:
            await Notification(
                user_id=user_id,
                title=title,
                body=body,
                sent_at=datetime.utcnow(),
                status="success",
            ).insert()
            return True
        except Exception as e:
            Logger.error(f"Failed to log notification: {e}")
            return False


notification_service = NotificationService()
