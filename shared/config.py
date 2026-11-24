import os
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

ReasoningEffort = Literal["none", "low", "medium", "high", "xhigh", "max"]
_REASONING_EFFORTS: dict[str, ReasoningEffort] = {
	"none": "none",
	"low": "low",
	"medium": "medium",
	"high": "high",
	"xhigh": "xhigh",
	"max": "max",
}

OPENAI_MODELS = {
	"profile_builder": os.getenv("OPENAI_PROFILE_BUILDER_MODEL", "gpt-6-luna"),
	"job_normalizer": os.getenv("OPENAI_JOB_NORMALIZER_MODEL", "gpt-6-luna"),
	"job_matching": os.getenv("OPENAI_JOB_MATCHING_MODEL", "gpt-6-luna"),
	"cv_tailoring": os.getenv("OPENAI_CV_TAILORING_MODEL", "gpt-6-luna"),
	"cover_letter_tailoring": os.getenv("OPENAI_COVER_LETTER_TAILORING_MODEL", "gpt-6-luna"),
}
OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "60"))

def _get_reasoning_effort() -> ReasoningEffort:
	value = os.getenv("OPENAI_REASONING_EFFORT", "medium")
	try:
		return _REASONING_EFFORTS[value]
	except KeyError as error:
		allowed = ", ".join(_REASONING_EFFORTS)
		raise ValueError(f"OPENAI_REASONING_EFFORT must be one of: {allowed}") from error


OPENAI_REASONING_EFFORT = _get_reasoning_effort()

ORIGINS = os.getenv("ORIGINS", "http://localhost:4200,http://127.0.0.1:4200,http://localhost:5173,http://127.0.0.1:5173")

# Keycloak (OIDC) — the API is a resource server that only validates Keycloak-issued access tokens.
KEYCLOAK_SERVER_URL = os.getenv("KEYCLOAK_SERVER_URL", "http://localhost:8080").rstrip("/")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "job-process")
KEYCLOAK_ISSUER = os.getenv("KEYCLOAK_ISSUER") or f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}"
# Back-channel JWKS URL; override when the API reaches Keycloak on a different host than the public issuer.
KEYCLOAK_JWKS_URL = os.getenv("KEYCLOAK_JWKS_URL") or f"{KEYCLOAK_ISSUER}/protocol/openid-connect/certs"
KEYCLOAK_AUDIENCE = os.getenv("KEYCLOAK_AUDIENCE", "job-process-api")
KEYCLOAK_ADMIN_ROLE = os.getenv("KEYCLOAK_ADMIN_ROLE", "admin")
KEYCLOAK_JWKS_CACHE_SECONDS = int(os.getenv("KEYCLOAK_JWKS_CACHE_SECONDS", "3600"))
