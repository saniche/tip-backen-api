from shared.database import TestingSessionLocal
from shared.models import UserProfile
from tests.keycloak_stub import issue_token


def _auth(client, email):
    token = issue_token(client, email)[
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
    return client.post("/api/v1/profile", headers=headers, json={"data": {"summary": "first"}}).json()["user_id"]


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


def test_current_profile_label_is_returned_by_update_and_get(client):
    headers = _auth(client, "profile-label@example.com")
    created = client.post("/api/v1/profile", headers=headers, json={"data": {}})

    updated = client.put(
        f"/api/v1/profile/{created.json()['id']}",
        headers=headers,
        json={"data": {"summary": "Python engineer"}, "label": "Engineering profile"},
    )

    assert updated.status_code == 200
    assert updated.json()["label"] == "Engineering profile"

    current = client.get("/api/v1/profile", headers=headers)

    assert current.status_code == 200
    assert current.json()["label"] == "Engineering profile"


def test_put_updates_selected_profile_without_changing_default(client):
    headers = _auth(client, "put-selected@example.com")
    first = client.post(
        "/api/v1/profile",
        headers=headers,
        json={"data": {"summary": "first", "skills": ["Python"]}, "output_language": "French"},
    )
    second = client.post(
        "/api/v1/profile", headers=headers, json={"data": {"summary": "second"}, "output_language": "French"}
    )
    assert first.status_code == second.status_code == 201
    older, newest = first.json()["id"], second.json()["id"]
    assert older != newest
    assert client.get("/api/v1/profile", headers=headers).json()["id"] == newest
    with TestingSessionLocal() as db:
        db.get(UserProfile, older).evidence = {"summary": "extracted", "skills": "extracted"}
        db.commit()

    updated = client.put(
        f"/api/v1/profile/{older}",
        headers=headers,
        json={"data": {"summary": {"value": "edited"}}, "label": " Backend "},
    )

    assert updated.status_code == 200
    assert updated.json()["id"] == older
    assert updated.json()["data"] == {"summary": "edited", "skills": ["Python"]}
    assert updated.json()["label"] == "Backend"
    assert updated.json()["output_language"] == "English"
    assert client.get("/api/v1/profile", headers=headers).json() == second.json()
    with TestingSessionLocal() as db:
        assert db.get(UserProfile, older).evidence == {"summary": "user_edited", "skills": "extracted"}


def test_put_rejects_missing_deleted_and_other_users_profiles(client):
    owner = _auth(client, "put-owner@example.com")
    other = _auth(client, "put-other@example.com")
    assert client.post("/api/v1/profile", json={"data": {}}).status_code == 401
    assert client.post("/api/v1/profile", headers=owner, json={}).status_code == 422
    profile = client.post("/api/v1/profile", headers=owner, json={"data": {"summary": "private"}}).json()
    path = f"/api/v1/profile/{profile['id']}"

    assert client.put(path, headers=other, json={"data": {"summary": "intrusion"}}).status_code == 404
    assert client.put("/api/v1/profile/missing", headers=owner, json={"data": {}}).status_code == 404
    assert client.put(path, json={"data": {}}).status_code == 401
    assert client.put(path, headers=owner, json={"output_language": "English"}).status_code == 422
    assert client.get("/api/v1/profile", headers=owner).json() == profile
    assert client.delete(f"/api/v1/profiles/{profile['id']}", headers=owner).status_code == 204
    assert client.put(path, headers=owner, json={"data": {"summary": "revived"}}).status_code == 404
    assert client.get("/api/v1/profiles", headers=owner).json() == []
    assert client.put("/api/v1/profile", headers=owner, json={"data": {}}).status_code == 405


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
