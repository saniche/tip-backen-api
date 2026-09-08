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
from typing import Type, TypeVar

import httpx
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


async def call_openai_structured(system: str, user: str, schema_model: Type[T], model: str = "gpt-4o-mini") -> T:
    schema = schema_model.model_json_schema()

    async with httpx.AsyncClient(timeout=60) as client:
        res = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": model,
                "temperature": 0,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": schema_model.__name__, "schema": schema, "strict": True},
                },
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        res.raise_for_status()
        data = res.json()

    content = data["choices"][0]["message"]["content"]
    return schema_model.model_validate_json(content)
