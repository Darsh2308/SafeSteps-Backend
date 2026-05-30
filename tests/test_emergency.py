import pytest

def get_auth_headers(client):
    client.post("/auth/send-otp", json={"phoneNumber": "+15559876543"})
    res = client.post("/auth/verify-otp", json={
        "phoneNumber": "+15559876543",
        "code": "123456"
    })
    return {"Authorization": f"Bearer {res.json()['token']}"}

def test_emergency_contacts_flow(client):
    headers = get_auth_headers(client)

    # 1. Add Contacts
    c1 = {"name": "Alice Jenkins", "relationship": "Mother", "phoneNumber": "+15551112222", "priority": "Primary"}
    c2 = {"name": "Bob Jenkins", "relationship": "Father", "phoneNumber": "+15552223333", "priority": "Secondary"}
    c3 = {"name": "Charlie Vance", "relationship": "Brother", "phoneNumber": "+15553334444", "priority": "Tertiary"}
    c4 = {"name": "Diana Vance", "relationship": "Sister", "phoneNumber": "+15554445555", "priority": "Secondary"}

    # Add 3 successfully
    r1 = client.post("/contacts", json=c1, headers=headers)
    assert r1.status_code == 201
    c1_id = r1.json()["id"]

    r2 = client.post("/contacts", json=c2, headers=headers)
    assert r2.status_code == 201

    r3 = client.post("/contacts", json=c3, headers=headers)
    assert r3.status_code == 201

    # Adding a 4th should exceed limit of 3
    r4 = client.post("/contacts", json=c4, headers=headers)
    assert r4.status_code == 400
    assert "maximum of 3 emergency contacts" in r4.json()["detail"]

    # 2. Get contacts list
    r_list = client.get("/contacts", headers=headers)
    assert r_list.status_code == 200
    assert len(r_list.json()) == 3

    # 3. Update Contact
    c1_up = {"name": "Alice Jenkins Updated", "relationship": "Mother", "phoneNumber": "+15551119999", "priority": "Primary"}
    r_up = client.put(f"/contacts/{c1_id}", json=c1_up, headers=headers)
    assert r_up.status_code == 200
    assert r_up.json()["name"] == "Alice Jenkins Updated"

    # 4. Delete Contact
    r_del = client.delete(f"/contacts/{c1_id}", headers=headers)
    assert r_del.status_code == 200
    r_list2 = client.get("/contacts", headers=headers)
    assert len(r_list2.json()) == 2

def test_emergency_session_lifecycle(client):
    headers = get_auth_headers(client)

    # 1. Start Session
    r_start = client.post("/emergency/start", headers=headers)
    assert r_start.status_code == 200
    res_start = r_start.json()
    assert "session_id" in res_start
    session_id = res_start["session_id"]

    # 2. Update Location
    r_loc = client.post("/location/update", json={
        "latitude": 37.7749,
        "longitude": -122.4194,
        "accuracy": 5.0,
        "speed": 12.5,
        "heading": 90.0
    }, headers=headers)
    assert r_loc.status_code == 200

    # 3. Fetch latest location
    r_loc_get = client.get(f"/location/{session_id}", headers=headers)
    assert r_loc_get.status_code == 200
    assert r_loc_get.json()["latitude"] == 37.7749

    # 4. Add custom timeline event
    r_time = client.post("/timeline/event", json={"event": "SMS Alert Sent"}, headers=headers)
    assert r_time.status_code == 201

    # 5. Fetch timeline history
    r_time_get = client.get(f"/timeline/{session_id}", headers=headers)
    assert r_time_get.status_code == 200
    events = [e["event"] for e in r_time_get.json()]
    assert "SOS Activated" in events
    assert "SMS Alert Sent" in events

    # 6. End Session and generate report
    r_end = client.post("/emergency/end", headers=headers)
    assert r_end.status_code == 200
    res_end = r_end.json()
    assert res_end["id"] == session_id
    assert res_end["duration"] != "Active"
    assert "SOS Deactivated" in [e["event"] for e in res_end["timeline"]]
