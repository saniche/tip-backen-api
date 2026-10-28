import pytest

from shared.database import TestingSessionLocal
from shared.models import UserDocument

PATHS = ["/api/v1/defaults/cv", "/api/v1/defaults/cover-letter"]


def _auth(client, email):
    token = client.post("/api/v1/auth/register", json={"email": email, "password": "password123"}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("path", PATHS)
def test_default_document_add_update_read_delete(client, path):
    headers = _auth(client, f"defaults{path[-5:]}@example.com")

    assert client.get(path, headers=headers).status_code == 404

    created = client.put(path, headers=headers, json={"content": "First version", "filename": "mine.md"})
    assert created.status_code == 200 and created.json()["content"] == "First version"

    updated = client.put(path, headers=headers, json={"content": "Second version"})
    assert updated.status_code == 200
    assert client.get(path, headers=headers).json()["content"] == "Second version"
    assert client.get(path, headers=headers).json()["filename"] is None

    assert client.delete(path, headers=headers).status_code == 204
    assert client.get(path, headers=headers).status_code == 404
    assert client.delete(path, headers=headers).status_code == 404


def test_only_one_document_per_kind_per_user_and_kinds_are_independent(client):
    headers = _auth(client, "one-each@example.com")

    for _ in range(3):
        client.put(PATHS[0], headers=headers, json={"content": "cv"})
    client.put(PATHS[1], headers=headers, json={"content": "letter"})

    with TestingSessionLocal() as db:
        kinds = sorted(item.kind for item in db.query(UserDocument).all())
    assert kinds == ["cover_letter", "cv"]
    assert client.get(PATHS[0], headers=headers).json()["content"] == "cv"
    assert client.get(PATHS[1], headers=headers).json()["content"] == "letter"


def test_default_documents_are_private_to_their_owner(client):
    owner, other = _auth(client, "owner-doc@example.com"), _auth(client, "other-doc@example.com")
    client.put(PATHS[0], headers=owner, json={"content": "secret cv"})

    assert client.get(PATHS[0], headers=other).status_code == 404
    assert client.delete(PATHS[0], headers=other).status_code == 404
    client.put(PATHS[0], headers=other, json={"content": "their own"})
    assert client.get(PATHS[0], headers=owner).json()["content"] == "secret cv"


@pytest.mark.parametrize("body", [{"content": ""}, {"content": "   "}, {"content": "x" * 50_001}, {"nope": 1}])
def test_default_document_rejects_invalid_bodies(client, body):
    headers = _auth(client, "invalid-doc@example.com")

    assert client.put(PATHS[0], headers=headers, json=body).status_code == 422


def test_default_documents_require_authentication(client):
    assert client.get(PATHS[0]).status_code in (401, 403)
