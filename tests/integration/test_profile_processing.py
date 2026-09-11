import time


def test_profile_processing_completes_and_preserves_edit(client):
    token = client.post("/api/v1/auth/register", json={"email": "profile-int@example.com", "password": "password123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    session = client.post("/api/v1/profile/sessions", headers=headers).json()

    upload = client.post(
        f"/api/v1/profile/sessions/{session['id']}/files",
        headers=headers,
        files={"file": ("resume.txt", b"Python engineer", "text/plain")},
    )
    assert upload.status_code == 202
    for _ in range(20):
        profile = client.get("/api/v1/profile", headers=headers)
        if profile.status_code == 200:
            break
        time.sleep(0.01)
    assert profile.status_code == 200

    updated = client.put("/api/v1/profile", headers=headers, json={"data": {"summary": "user confirmed"}})
    assert updated.status_code == 200
    assert updated.json()["data"]["summary"] == "user confirmed"