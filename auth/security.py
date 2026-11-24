"""
Keycloak (OIDC) bearer-token authentication.

The API is an OAuth2 resource server: Keycloak authenticates users and issues RS256 access tokens; this
module validates them against the realm's JWKS and resolves the local `users` row (created/updated on the
fly by `auth.user_sync`). No credentials are stored or verified here.
"""

import logging
import threading
import time
from typing import Any

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.orm import Session

import shared.config as config
from auth.user_sync import sync_user_from_claims
from shared.database import get_db
from shared.models import User

logger = logging.getLogger(__name__)

ALGORITHMS = ["RS256"]
# Minimum gap between forced JWKS refreshes triggered by an unknown `kid`, so garbage tokens can't
# make us hammer Keycloak.
_MIN_REFRESH_INTERVAL_SECONDS = 10

bearer_scheme = HTTPBearer(
    scheme_name="BearerAuth",
    description="Paste a Keycloak access token for the job-process realm.",
    auto_error=False,
)


def user_is_admin(user: User) -> bool:
    return getattr(user, "role", "user") == "admin"


class IdentityProviderUnavailable(Exception):
    pass


class JwksCache:
    """Caches the realm signing keys; refetches on TTL expiry or when a token carries an unknown `kid`."""

    def __init__(self, url: str, ttl_seconds: int):
        self.url = url
        self.ttl_seconds = ttl_seconds
        self._keys: dict[str, dict[str, Any]] = {}
        self._fetched_at = 0.0
        self._lock = threading.Lock()

    def _fetch(self) -> dict[str, Any]:
        response = httpx.get(self.url, timeout=5.0)
        response.raise_for_status()
        return response.json()

    def _refresh(self) -> None:
        try:
            document = self._fetch()
        except Exception as error:  # network/HTTP/JSON failures
            logger.warning("Could not fetch Keycloak JWKS from %s: %s", self.url, error)
            if not self._keys:
                raise IdentityProviderUnavailable() from error
            return  # keep serving the previously cached keys
        self._keys = {key["kid"]: key for key in document.get("keys", []) if key.get("kid")}
        self._fetched_at = time.monotonic()

    def get_key(self, kid: str) -> dict[str, Any] | None:
        with self._lock:
            age = time.monotonic() - self._fetched_at
            if not self._keys or age > self.ttl_seconds:
                self._refresh()
            elif kid not in self._keys and age > _MIN_REFRESH_INTERVAL_SECONDS:
                self._refresh()  # key rotation
            return self._keys.get(kid)

    def clear(self) -> None:
        with self._lock:
            self._keys = {}
            self._fetched_at = 0.0


jwks_cache = JwksCache(config.KEYCLOAK_JWKS_URL, config.KEYCLOAK_JWKS_CACHE_SECONDS)


def _unauthorized(detail: str = "Could not validate credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Validate signature, expiry, issuer and audience of a Keycloak access token and return its claims."""
    try:
        header = jwt.get_unverified_header(token)
    except JWTError:
        raise _unauthorized()
    kid = header.get("kid")
    if not kid or header.get("alg") not in ALGORITHMS:
        raise _unauthorized()

    try:
        key = jwks_cache.get_key(kid)
    except IdentityProviderUnavailable:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Identity provider unavailable")
    if key is None:
        raise _unauthorized()

    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=ALGORITHMS,
            audience=config.KEYCLOAK_AUDIENCE,
            issuer=config.KEYCLOAK_ISSUER,
            options={"require_exp": True, "require_iss": True, "require_aud": True, "require_sub": True},
        )
    except ExpiredSignatureError:
        raise _unauthorized("Token has expired")
    except JWTError:
        raise _unauthorized()

    if not claims.get("sub"):
        raise _unauthorized()
    return claims


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise _unauthorized()
    claims = decode_access_token(credentials.credentials)
    user = sync_user_from_claims(db, claims)
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    return user
