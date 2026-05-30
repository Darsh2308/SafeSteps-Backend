from datetime import datetime
from beanie import Document
from pydantic import Field


class Notification(Document):
    user_id: str
    title: str
    body: str
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "success"  # "success" | "failed"

    class Settings:
        name = "notifications"
