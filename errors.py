import logging
from typing import Any

from fastapi import HTTPException

logger = logging.getLogger("tip-api")


class AppException(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Any | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


def safe_message(value: Any, fallback: str = "The request could not be processed.") -> str:
    message = str(value).strip() if value is not None else ""
    if not message:
        return fallback
    lowered = message.lower()
    if any(
        marker in lowered for marker in ["api key", "secret", "token", "password", "authorization", "azure", "openai"]
    ):
        return fallback
    if len(message) > 280:
        return fallback
    return message


def translate_exception(exc: Exception) -> AppException:
    if isinstance(exc, HTTPException):
        code_map = {
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "RESOURCE_NOT_FOUND",
            409: "CONFLICT",
            422: "VALIDATION_ERROR",
        }
        return AppException(
            str(exc.detail),
            code=code_map.get(exc.status_code, "VALIDATION_ERROR"),
            status_code=exc.status_code,
            details=None,
        )

    lowered = str(exc).lower()
    if any(marker in lowered for marker in ["openai", "api key", "rate limit", "llm", "provider"]):
        return AppException(
            "External processing failed. Please try again later.", code="SERVICE_UNAVAILABLE", status_code=502
        )
    if any(marker in lowered for marker in ["blob", "storage", "azure"]):
        return AppException(
            "Storage is temporarily unavailable. Please try again later.", code="SERVICE_UNAVAILABLE", status_code=503
        )
    return AppException("An unexpected error occurred.", code="INTERNAL_ERROR", status_code=500)
