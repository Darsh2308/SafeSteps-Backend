from tests.conftest import register_and_login

CONTACT_1 = {"name": "Alice Jenkins", "relationship": "Mother", "phoneNumber": "+15551112222", "priority": "Primary"}
CONTACT_2 = {"name": "Bob Jenkins",   "relationship": "Father", "phoneNumber": "+15552223333", "priority": "Secondary"}
CONTACT_3 = {"name": "Charlie Vance", "relationship": "Brother","phoneNumber": "+15553334444", "priority": "Tertiary"}
CONTACT_4 = {"name": "Diana Vance",   "relationship": "Sister", "phoneNumber": "+15554445555", "priority": "Secondary"}


def test_emergency_contacts_crud(client):
    headers = register_and_login(client, "+15559876543")

    # Add 3 contacts successfully
    r1 = client.post("/contacts", json=CONTACT_1, headers=headers)
    assert r1.status_code == 201
    c1_id = r1.json()["id"]

    assert client.post("/contacts", json=CONTACT_2, headers=headers).status_code == 201
    assert client.post("/contacts", json=CONTACT_3, headers=headers).status_code == 201

    # 4th contact must be rejected
    r4 = client.post("/contacts", json=CONTACT_4, headers=headers)
    assert r4.status_code == 400
    assert "3" in r4.json()["detail"].lower() or "maximum" in r4.json()["detail"].lower()

    # List returns exactly 3
    r_list = client.get("/contacts", headers=headers)
    assert r_list.status_code == 200
    assert len(r_list.json()) == 3

    # Update first contact
    r_up = client.put(f"/contacts/{c1_id}", json={
        "name": "Alice Updated", "relationship": "Mother",
        "phoneNumber": "+15551119999", "priority": "Primary"
    }, headers=headers)
    assert r_up.status_code == 200
    assert r_up.json()["name"] == "Alice Updated"

    # Delete first contact — list shrinks to 2
    assert client.delete(f"/contacts/{c1_id}", headers=headers).status_code == 200
    r_list2 = client.get("/contacts", headers=headers)
    assert len(r_list2.json()) == 2


def test_emergency_session_lifecycle(client):
    headers = register_and_login(client, "+15558001000")

    # Start session
    r_start = client.post("/emergency/start", headers=headers)
    assert r_start.status_code == 200
    session_id = r_start.json()["session_id"]
    assert session_id

    # Current session must be returned
    r_current = client.get("/emergency/current", headers=headers)
    assert r_current.status_code == 200
    assert r_current.json()["session_id"] == session_id

    # Update location
    r_loc = client.post("/location/update", json={
        "latitude": 19.0760, "longitude": 72.8777,
        "accuracy": 5.0, "speed": 8.3, "heading": 45.0
    }, headers=headers)
    assert r_loc.status_code == 200
    assert r_loc.json()["success"] is True
    assert "maps_link" in r_loc.json()

    # Fetch latest location
    r_loc_get = client.get(f"/location/{session_id}", headers=headers)
    assert r_loc_get.status_code == 200
    assert r_loc_get.json()["latitude"] == 19.0760

    # Location history has one entry
    r_hist = client.get(f"/location/history/{session_id}", headers=headers)
    assert r_hist.status_code == 200
    assert len(r_hist.json()) == 1

    # Add custom timeline event
    r_time = client.post("/timeline/event", json={"event": "SMS Alert Sent"}, headers=headers)
    assert r_time.status_code == 201

    # Timeline has SOS Activated + GPS + SMS Alert Sent
    r_time_get = client.get(f"/timeline/{session_id}", headers=headers)
    assert r_time_get.status_code == 200
    events = [e["event"] for e in r_time_get.json()]
    assert "SOS Activated" in events
    assert "SMS Alert Sent" in events

    # End session
    r_end = client.post("/emergency/end", headers=headers)
    assert r_end.status_code == 200
    res_end = r_end.json()
    assert res_end["id"] == session_id
    assert res_end["duration"] != "Active"
    timeline_events = [e["event"] for e in res_end["timeline"]]
    assert any("SOS Deactivated" in ev for ev in timeline_events)

    # No active session after ending — endpoint returns 200 with null body
    r_current2 = client.get("/emergency/current", headers=headers)
    assert r_current2.status_code == 200
    assert r_current2.json() is None


def test_incident_history(client):
    headers = register_and_login(client, "+15558002000")

    # Create and immediately close a session
    client.post("/emergency/start", headers=headers)
    client.post("/emergency/end", headers=headers)

    r = client.get("/emergency/incidents", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_starting_new_session_closes_active(client):
    headers = register_and_login(client, "+15558003000")

    r1 = client.post("/emergency/start", headers=headers)
    sid1 = r1.json()["session_id"]

    # Second start should implicitly close the first
    r2 = client.post("/emergency/start", headers=headers)
    assert r2.status_code == 200
    sid2 = r2.json()["session_id"]
    assert sid2 != sid1

    # Only one active session now
    r_current = client.get("/emergency/current", headers=headers)
    assert r_current.json()["session_id"] == sid2
