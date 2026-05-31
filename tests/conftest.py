import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from app.main import app


async def _mock_init_db():
    from beanie import init_beanie
    from app.models.user import User
    from app.models.contact import EmergencyContact
    from app.models.session import EmergencySession
    from app.models.notification import Notification

    client = AsyncMongoMockClient()
    db = client["test_safesteps"]
    await init_beanie(
        database=db,
        document_models=[User, EmergencyContact, EmergencySession, Notification],
    )


@pytest.fixture(scope="function")
def client():
    with patch("app.main.init_db", _mock_init_db):
        with TestClient(app) as c:
            yield c


def register_and_login(client, phone: str = "+15550000001") -> dict:
    r = client.post("/auth/register", json={
        "phone": phone,
        "full_name": "Test User",
        "age": "25",
        "preferred_language": "English",
    })
    if r.status_code == 400:
        r = client.post("/auth/login", json={"phone": phone})
    assert r.status_code in (200, 201), r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}
