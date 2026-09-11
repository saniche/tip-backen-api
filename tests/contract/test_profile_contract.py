def test_profile_session_upload_and_edit_preserves_profile(client):
    token = client.post(
        "/api/v1/auth/register", json={"email": "profile@example.com", "password": "password123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    session = client.post("/api/v1/profile/sessions", headers=headers)
    assert session.status_code == 201
    uploaded = client.post(
        f"/api/v1/profile/sessions/{session.json()['id']}/files",
        headers=headers,
        files={"file": ("resume.txt", b"Python engineer", "text/plain")},
    )
    assert uploaded.status_code == 202
    profile = client.get("/api/v1/profile", headers=headers)
    assert profile.status_code == 200
    updated = client.put("/api/v1/profile", headers=headers, json={"data": {"summary": "confirmed"}})
    assert updated.status_code == 200
    assert updated.json()["data"]["summary"] == "confirmed"
