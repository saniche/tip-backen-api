from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

import auth.security as auth_security
from auth.user_sync import sync_user_from_claims
from shared.models import Job, User
from tests.keycloak_stub import TEST_AUDIENCE, TEST_ISSUER, issue_token, jwks, make_token


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def _me(client, token):
    return client.get("/api/v1/auth/me", headers=_bearer(token))


def test_valid_token_provisions_local_user(client, database_session):
    response = _me(client, make_token("New.User@Example.com", sub="kc-123", roles=["user"]))

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "New.User@Example.com"
    assert body["role"] == "user"
    assert body["email_verified"] is True
    assert body["first_name"] == "Test"
    user = database_session.query(User).filter_by(keycloak_sub="kc-123").one()
    assert user.id == body["id"]
    assert user.last_login_at is not None


def test_repeated_requests_reuse_the_same_user(client, database_session):
    token = make_token("same@example.com", sub="kc-same")
    first = _me(client, token).json()["id"]
    second = _me(client, token).json()["id"]
    assert first == second
    assert database_session.query(User).filter_by(keycloak_sub="kc-same").count() == 1


@pytest.mark.parametrize(
    "token_kwargs",
    [
        {"expires_in": -60},
        {"issuer": "http://evil.test/realms/job-process"},
        {"audience": "some-other-client"},
    ],
    ids=["expired", "wrong-issuer", "wrong-audience"],
)
def test_rejects_invalid_claims(client, token_kwargs):
    response = _me(client, make_token("claims@example.com", **token_kwargs))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_accepts_audience_list_containing_api(client):
    response = _me(client, make_token("aud@example.com", audience=["account", TEST_AUDIENCE]))
    assert response.status_code == 200


def test_rejects_tampered_signature(client):
    header, payload, _ = make_token("sig@example.com").split(".")
    _, _, other_signature = make_token("other@example.com").split(".")
    assert _me(client, f"{header}.{payload}.{other_signature}").status_code == 401


def test_rejects_token_signed_by_unknown_key(client):
    assert _me(client, make_token("rogue@example.com", kid="rogue-key")).status_code == 401


def test_rejects_missing_and_malformed_tokens(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert _me(client, "not-a-jwt").status_code == 401


def test_unknown_kid_triggers_jwks_refresh(client, monkeypatch):
    calls = []

    def fetch():
        calls.append(1)
        return jwks() if len(calls) == 1 else jwks("test-signing-key", "rotated-key")

    auth_security.jwks_cache.clear()
    monkeypatch.setattr(auth_security.jwks_cache, "_fetch", fetch)
    monkeypatch.setattr(auth_security, "_MIN_REFRESH_INTERVAL_SECONDS", -1)

    assert _me(client, make_token("before@example.com")).status_code == 200
    assert _me(client, make_token("rotated@example.com", kid="rotated-key")).status_code == 200
    assert len(calls) == 2


def test_identity_provider_outage_returns_503(client, monkeypatch):
    def fail():
        raise ConnectionError("keycloak down")

    auth_security.jwks_cache.clear()
    monkeypatch.setattr(auth_security.jwks_cache, "_fetch", fail)
    assert _me(client, make_token("down@example.com")).status_code == 503


def test_admin_role_from_realm_or_client_roles(client):
    realm_admin = _me(client, make_token("realm-admin@example.com", roles=["user", "admin"]))
    client_admin = _me(
        client,
        make_token(
            "client-admin@example.com",
            roles=["user"],
            extra={"resource_access": {TEST_AUDIENCE: {"roles": ["admin"]}}},
        ),
    )
    assert realm_admin.json()["role"] == "admin"
    assert client_admin.json()["role"] == "admin"


def test_role_is_revoked_when_keycloak_role_removed(client):
    assert _me(client, make_token("demote@example.com", roles=["admin"])).json()["role"] == "admin"
    assert _me(client, make_token("demote@example.com", roles=["user"])).json()["role"] == "user"


def test_admin_from_keycloak_gets_write_access_to_other_users_jobs(client, database_session):
    owner = issue_token(client, "owner@example.com")
    job = Job(title="Owned", url="https://jobs.test/owned", status="completed", submitter_id=owner["user_id"])
    database_session.add(job)
    database_session.commit()

    admin_token = make_token("admin@example.com", roles=["admin"])
    response = client.get(f"/api/v1/jobs/{job.id}", headers=_bearer(admin_token))
    assert response.status_code == 200
    assert response.json()["has_write_access"] is True


def test_legacy_user_is_linked_by_verified_email(client, database_session):
    legacy = User(email="Legacy@Example.com")
    database_session.add(legacy)
    database_session.commit()

    response = _me(client, make_token("legacy@example.com", sub="kc-legacy"))

    assert response.status_code == 200
    assert response.json()["id"] == legacy.id
    database_session.refresh(legacy)
    assert legacy.keycloak_sub == "kc-legacy"
    assert database_session.query(User).count() == 1


def test_legacy_user_is_not_linked_with_unverified_email(client, database_session):
    database_session.add(User(email="unverified@example.com"))
    database_session.commit()

    response = _me(client, make_token("unverified@example.com", sub="kc-unverified", email_verified=False))

    assert response.status_code == 403
    assert database_session.query(User).filter_by(keycloak_sub="kc-unverified").count() == 0


def test_email_owned_by_another_keycloak_identity_conflicts(client):
    assert _me(client, make_token("taken@example.com", sub="kc-first")).status_code == 200
    assert _me(client, make_token("taken@example.com", sub="kc-second")).status_code == 409


def test_email_change_in_keycloak_is_synced(client):
    first = _me(client, make_token("old@example.com", sub="kc-mover")).json()
    second = _me(client, make_token("new@example.com", sub="kc-mover")).json()
    assert first["id"] == second["id"]
    assert second["email"] == "new@example.com"


def test_disabled_local_user_is_forbidden(client, database_session):
    token = make_token("disabled@example.com", sub="kc-disabled")
    assert _me(client, token).status_code == 200
    user = database_session.query(User).filter_by(keycloak_sub="kc-disabled").one()
    user.is_active = False
    database_session.commit()

    response = _me(client, token)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_token_without_email_is_rejected(database_session):
    with pytest.raises(HTTPException) as error:
        sync_user_from_claims(database_session, {"sub": "kc-no-email", "iss": TEST_ISSUER})
    assert error.value.status_code == 403


def test_last_login_is_only_refreshed_after_interval(database_session):
    claims = {"sub": "kc-login", "email": "login@example.com", "email_verified": True}
    user = sync_user_from_claims(database_session, claims)
    first_login = user.last_login_at

    assert sync_user_from_claims(database_session, claims).last_login_at == first_login

    user.last_login_at = datetime.now(timezone.utc) - timedelta(hours=1)
    database_session.commit()
    refreshed = sync_user_from_claims(database_session, claims).last_login_at.replace(tzinfo=timezone.utc)
    assert refreshed > datetime.now(timezone.utc) - timedelta(minutes=1)


def test_register_and_login_endpoints_are_gone(client):
    assert client.post("/api/v1/auth/register", json={}).status_code in (404, 405)
    assert client.post("/api/v1/auth/login", json={}).status_code in (404, 405)
