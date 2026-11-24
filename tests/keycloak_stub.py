"""Test double for Keycloak: an in-memory RSA signing key, its JWKS, and helpers to mint access tokens."""

import base64
import time
import uuid
from functools import lru_cache

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt

TEST_ISSUER = "http://keycloak.test/realms/job-process"
TEST_AUDIENCE = "job-process-api"
TEST_KID = "test-signing-key"


def _b64url_uint(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


@lru_cache(maxsize=None)
def signing_key(kid: str = TEST_KID) -> tuple[bytes, dict]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private_key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    numbers = private_key.public_key().public_numbers()
    jwk = {"kty": "RSA", "kid": kid, "use": "sig", "alg": "RS256", "n": _b64url_uint(numbers.n),
           "e": _b64url_uint(numbers.e)}
    return pem, jwk


def jwks(*kids: str) -> dict:
    return {"keys": [signing_key(kid)[1] for kid in (kids or (TEST_KID,))]}


def make_token(
    email: str,
    *,
    sub: str | None = None,
    roles: list[str] | None = None,
    email_verified: bool = True,
    issuer: str = TEST_ISSUER,
    audience: str | list[str] = TEST_AUDIENCE,
    expires_in: int = 300,
    kid: str = TEST_KID,
    extra: dict | None = None,
) -> str:
    now = int(time.time())
    claims = {
        "sub": sub or str(uuid.uuid5(uuid.NAMESPACE_URL, f"keycloak-test:{email.lower()}")),
        "iss": issuer,
        "aud": audience,
        "azp": "job-process-web",
        "iat": now,
        "exp": now + expires_in,
        "email": email,
        "email_verified": email_verified,
        "preferred_username": email,
        "given_name": "Test",
        "family_name": "User",
        "realm_access": {"roles": roles if roles is not None else ["user"]},
    }
    claims.update(extra or {})
    pem, _ = signing_key(kid)
    return jwt.encode(claims, pem, algorithm="RS256", headers={"kid": kid})


def issue_token(client, email: str, **kwargs) -> dict:
    """Simulate a Keycloak sign-in: mint a token and make the first API call that provisions the user.

    Returns `{"access_token": ..., "user_id": ...}` so tests can build headers and look up the user.
    """
    token = make_token(email, **kwargs)
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, response.text
    return {"access_token": token, "token_type": "bearer", "user_id": response.json()["id"]}


def auth_headers(client, email: str, **kwargs) -> dict:
    return {"Authorization": f"Bearer {issue_token(client, email, **kwargs)['access_token']}"}
