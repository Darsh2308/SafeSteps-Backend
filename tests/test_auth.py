from tests.conftest import register_and_login

PHONE = "+15551234567"

REGISTER_PAYLOAD = {
    "phone": PHONE,
    "full_name": "Jane Doe",
    "age": "30",
    "date_of_birth": "1994-05-15",
    "gender": "Female",
    "blood_group": "O+",
    "preferred_language": "English",
}


def test_register_success(client):
    r = client.post("/auth/register", json=REGISTER_PAYLOAD)
    assert r.status_code == 201
    data = r.json()
    assert data["success"] is True
    assert "token" in data
    assert data["user"]["phone"] == PHONE
    assert data["user"]["fullName"] == "Jane Doe"


def test_register_duplicate_phone(client):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    r = client.post("/auth/register", json=REGISTER_PAYLOAD)
    assert r.status_code == 400
    assert "already registered" in r.json()["detail"]


def test_login_success(client):
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    r = client.post("/auth/login", json={"phone": PHONE})
    assert r.status_code == 200
    assert r.json()["success"] is True
    assert "token" in r.json()


def test_login_unknown_phone(client):
    r = client.post("/auth/login", json={"phone": "+19999999999"})
    assert r.status_code == 404


def test_get_me(client):
    headers = register_and_login(client, PHONE)
    r = client.get("/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["phone"] == PHONE


def test_logout(client):
    headers = register_and_login(client, PHONE)
    r = client.post("/auth/logout", headers=headers)
    assert r.status_code == 200
    assert r.json()["success"] is True
