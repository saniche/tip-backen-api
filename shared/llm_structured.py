"""
Provider abstraction for structured LLM calls.

Every pipeline module needs the same thing: turn (system prompt, user content, an expected
Pydantic schema) into a validated instance of that schema. Before this change that need was met
by calling OpenAI's Chat Completions API directly from every call site's import of
`call_openai_structured` — correct behavior, but it meant "swap providers" would have meant
touching profile_builder.py, cv_tailoring.py, llm_matching.py, and job_service.py all at once.

Now there's one interface (StructuredLLMProvider) and one implementation (OpenAIProvider). Adding
a second provider is: write a new subclass, register it in _PROVIDERS, and point LLM_PROVIDER at
it — no pipeline module changes.

Note: OpenAI's strict json_schema mode has specific constraints (every property listed in
"required", nested objects need additionalProperties:false). Pydantic v2 models with
extra="forbid" satisfy this, but double-check with a real call before relying on it in production —
strict-mode compatibility has changed across API versions.
"""

import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Type, TypeVar

import httpx
from pydantic import BaseModel

from shared.config import OPENAI_MODELS, OPENAI_TIMEOUT_SECONDS

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger("tip-api")


class StructuredProviderError(Exception):
    """Safe failure raised when structured model processing cannot complete."""


class StructuredLLMProvider(ABC):
    """
    Interface every LLM provider implements. Callers depend on this, never on a vendor SDK or
    a specific HTTP API shape — that's what makes the provider swappable.
    """

    @abstractmethod
    async def complete(
        self, system: str, user: str, schema_model: Type[T], *, operation: str, model: str | None = None
    ) -> T:
        """Return a validated `schema_model` instance, or raise StructuredProviderError."""
        raise NotImplementedError


class OpenAIProvider(StructuredLLMProvider):
    """Calls OpenAI's Chat Completions API in strict json_schema mode."""

    def __init__(self, models: dict[str, str] | None = None, timeout_seconds: float | None = None):
        self._models = OPENAI_MODELS if models is None else models
        self._timeout_seconds = OPENAI_TIMEOUT_SECONDS if timeout_seconds is None else timeout_seconds

    def _model_for(self, operation: str, model: str | None) -> str:
        selected = model or self._models.get(operation)
        if not selected:
            raise StructuredProviderError("External processing is not configured.")
        return selected

    async def complete(
        self, system: str, user: str, schema_model: Type[T], *, operation: str, model: str | None = None
    ) -> T:
        started_at = time.perf_counter()
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise StructuredProviderError("External processing is not configured.")
        selected_model = self._model_for(operation, model)
        schema = schema_model.model_json_schema()
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": selected_model,
                        "temperature": 0,
                        "response_format": {
                            "type": "json_schema",
                            "json_schema": {"name": schema_model.__name__, "schema": schema, "strict": True},
                        },
                        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                    },
                )
                response.raise_for_status()
                message = response.json()["choices"][0]["message"]
            if message.get("refusal") or not message.get("content"):
                raise StructuredProviderError("External processing did not return a usable result.")
            result = schema_model.model_validate_json(message["content"])
            logger.info(
                "Structured provider completed",
                extra={
                    "operation": operation,
                    "model": selected_model,
                    "duration_ms": int((time.perf_counter() - started_at) * 1000),
                },
            )
            return result
        except StructuredProviderError:
            logger.warning(
                "Structured provider failed",
                extra={
                    "operation": operation,
                    "model": selected_model,
                    "duration_ms": int((time.perf_counter() - started_at) * 1000),
                },
            )
            raise
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            logger.warning(
                "Structured provider failed",
                extra={
                    "operation": operation,
                    "model": selected_model,
                    "duration_ms": int((time.perf_counter() - started_at) * 1000),
                },
            )
            raise StructuredProviderError("External processing failed.") from exc


_PROVIDERS: dict[str, Type[StructuredLLMProvider]] = {
    "openai": OpenAIProvider,
}

_active_provider: StructuredLLMProvider | None = None


def get_llm_provider() -> StructuredLLMProvider:
    """
    Returns the process-wide provider, selected once via the LLM_PROVIDER env var (default
    "openai") and cached. To add a real second provider: implement StructuredLLMProvider,
    add it to _PROVIDERS, set LLM_PROVIDER — nothing else in the app changes.
    """
    global _active_provider
    if _active_provider is None:
        provider_name = os.environ.get("LLM_PROVIDER", "openai")
        provider_cls = _PROVIDERS.get(provider_name)
        if provider_cls is None:
            raise StructuredProviderError(f"Unknown LLM_PROVIDER '{provider_name}'.")
        _active_provider = provider_cls()
    return _active_provider


def set_llm_provider(provider: StructuredLLMProvider | None) -> None:
    """
    Override (or reset, with None) the active provider. Intended for tests — inject a fake
    StructuredLLMProvider instead of monkeypatching HTTP calls or env vars.
    """
    global _active_provider
    _active_provider = provider


async def call_openai_structured(
    system: str, user: str, schema_model: Type[T], *, operation: str, model: str | None = None
) -> T:
    """
    Stable entry point already imported by every pipeline module. Despite the name — kept as-is
    for now so this change doesn't also have to touch five call sites — this delegates to
    whichever provider `get_llm_provider()` resolves, not to OpenAI specifically. A follow-up
    pass can rename this to `call_structured_llm()` across the codebase once a second provider
    actually exists and the name stops matching reality.
    """
    return await get_llm_provider().complete(system, user, schema_model, operation=operation, model=model)
