import pytest

def test_otp_auth_flow(client):
    # 1. Send OTP
    response = client.post("/auth/send-otp", json={"phoneNumber": "+15551234567"})
    assert response.status_code == 200
    assert response.json()["success"] is True

    # 2. Verify OTP
    response = client.post("/auth/verify-otp", json={
        "phoneNumber": "+15551234567",
        "code": "123456"
    })
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert "token" in res_data
    token = res_data["token"]
    assert res_data["user"]["phone"] == "+15551234567"

    # 3. GET /auth/me with Bearer token
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["phone"] == "+15551234567"

    # 4. PUT /auth/profile
    response = client.put("/auth/profile", json={
        "fullName": "Jane Doe",
        "age": "30",
        "dateOfBirth": "1996-01-01",
        "gender": "Female",
        "bloodGroup": "AB-Negative",
        "preferredLanguage": "Marathi",
        "themeDarkMode": False
    }, headers=headers)
    assert response.status_code == 200
    res_profile = response.json()
    assert res_profile["fullName"] == "Jane Doe"
    assert res_profile["preferredLanguage"] == "Marathi"
    assert res_profile["themeDarkMode"] is False

    # 5. GET /profile/settings
    response = client.get("/profile/settings", headers=headers)
    assert response.status_code == 200
    assert response.json()["themeDarkMode"] is False

    # 6. PUT /profile/language
    response = client.put("/profile/language", json={"language": "Hindi"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["preferredLanguage"] == "Hindi"
