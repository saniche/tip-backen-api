"""
Calls the LLM using a Pydantic model's own .model_json_schema() as the source of truth for the
expected output shape, instead of hand-writing a matching JSON-schema description in the prompt
(the pattern the earlier standalone modules used). One definition, no drift between the model and
the prompt.

Note: OpenAI's strict json_schema mode has specific constraints (every property listed in
"required", nested objects need additionalProperties:false). Pydantic v2 models with
extra="forbid" satisfy this, but double-check with a real call before relying on it in production —
strict-mode compatibility has changed across API versions.
"""

import os
import logging
import time
from typing import Type, TypeVar

import httpx
from pydantic import BaseModel

from config import OPENAI_MODELS, OPENAI_TIMEOUT_SECONDS

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger("tip-api")


class StructuredProviderError(Exception):
    """Safe failure raised when structured model processing cannot complete."""


def _model_for(operation: str, model: str | None) -> str:
    selected = model or OPENAI_MODELS.get(operation)
    if not selected:
        raise StructuredProviderError("External processing is not configured.")
    return selected


async def call_openai_structured(
    system: str, user: str, schema_model: Type[T], *, operation: str, model: str | None = None
) -> T:
    started_at = time.perf_counter()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise StructuredProviderError("External processing is not configured.")
    selected_model = _model_for(operation, model)
    schema = schema_model.model_json_schema()
    try:
        async with httpx.AsyncClient(timeout=OPENAI_TIMEOUT_SECONDS) as client:
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
            extra={"operation": operation, "model": selected_model, "duration_ms": int((time.perf_counter() - started_at) * 1000)},
        )
        return result
    except StructuredProviderError as exc:
        logger.warning(
            "Structured provider failed",
            extra={"operation": operation, "model": selected_model, "duration_ms": int((time.perf_counter() - started_at) * 1000)},
        )
        raise
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        logger.warning(
            "Structured provider failed",
            extra={"operation": operation, "model": selected_model, "duration_ms": int((time.perf_counter() - started_at) * 1000)},
        )
        raise StructuredProviderError("External processing failed.") from exc
