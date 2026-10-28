from shared.database import TestingSessionLocal
from shared.models import UserProfile


def _auth(client, email):
    token = client.post("/api/v1/auth/register", json={"email": email, "password": "password123"}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


def _add_profile(email_user_id, summary, created_offset):
    from datetime import datetime, timedelta, timezone

    with TestingSessionLocal() as db:
        profile = UserProfile(
            user_id=email_user_id,
            data={"summary": summary},
            evidence={},
            output_language="English",
            created_at=datetime.now(timezone.utc) + timedelta(seconds=created_offset),
        )
        db.add(profile)
        db.commit()
        return profile.id


def _user_id(client, headers):
    # the legacy PUT creates the first profile; its user_id is exposed in the response
    return client.put("/api/v1/profile", headers=headers, json={"data": {"summary": "first"}}).json()["user_id"]


def test_list_marks_latest_as_default_and_hides_data(client):
    headers = _auth(client, "multi@example.com")
    user_id = _user_id(client, headers)
    newest = _add_profile(user_id, "newest", 10)

    listing = client.get("/api/v1/profiles", headers=headers)

    assert listing.status_code == 200
    items = listing.json()
    assert [item["id"] for item in items][0] == newest
    assert [item["is_default"] for item in items] == [True, False]
    assert all("data" not in item for item in items)


def test_patch_updates_label_and_data_without_changing_default(client):
    headers = _auth(client, "patch@example.com")
    user_id = _user_id(client, headers)
    newest = _add_profile(user_id, "newest", 10)
    older = client.get("/api/v1/profiles", headers=headers).json()[1]["id"]

    patched = client.patch(
        f"/api/v1/profiles/{older}", headers=headers, json={"label": "Backend focus", "data": {"summary": "edited"}}
    )

    assert patched.status_code == 200
    assert patched.json()["label"] == "Backend focus"
    assert patched.json()["data"]["summary"] == "edited"
    assert patched.json()["is_default"] is False
    assert client.get("/api/v1/profiles", headers=headers).json()[0]["id"] == newest


def test_delete_is_soft_and_default_falls_back_to_previous_profile(client):
    headers = _auth(client, "delete@example.com")
    user_id = _user_id(client, headers)
    older = client.get("/api/v1/profiles", headers=headers).json()[0]["id"]
    newest = _add_profile(user_id, "newest", 10)

    assert client.delete(f"/api/v1/profiles/{newest}", headers=headers).status_code == 204

    items = client.get("/api/v1/profiles", headers=headers).json()
    assert [item["id"] for item in items] == [older]
    assert items[0]["is_default"] is True
    assert client.get(f"/api/v1/profiles/{newest}", headers=headers).status_code == 404
    assert client.get("/api/v1/profile", headers=headers).json()["id"] == older
    with TestingSessionLocal() as db:
        assert db.get(UserProfile, newest) is not None  # row kept so old results keep a valid FK


def test_profiles_are_scoped_to_their_owner(client):
    owner = _auth(client, "owner@example.com")
    _user_id(client, owner)
    profile_id = client.get("/api/v1/profiles", headers=owner).json()[0]["id"]
    other = _auth(client, "other@example.com")

    assert client.get(f"/api/v1/profiles/{profile_id}", headers=other).status_code == 404
    assert client.patch(f"/api/v1/profiles/{profile_id}", headers=other, json={"label": "x"}).status_code == 404
    assert client.delete(f"/api/v1/profiles/{profile_id}", headers=other).status_code == 404
    assert client.get("/api/v1/profiles", headers=other).json() == []


def test_patch_rejects_unknown_fields(client):
    headers = _auth(client, "strict@example.com")
    _user_id(client, headers)
    profile_id = client.get("/api/v1/profiles", headers=headers).json()[0]["id"]

    response = client.patch(f"/api/v1/profiles/{profile_id}", headers=headers, json={"unexpected": 1})

    assert response.status_code == 422
