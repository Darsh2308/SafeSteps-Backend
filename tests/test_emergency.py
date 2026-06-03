from tests.conftest import register_and_login


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
