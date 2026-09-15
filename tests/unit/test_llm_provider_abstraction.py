import pytest
from pydantic import BaseModel, ConfigDict

import shared.llm_structured as llm_structured
from shared.llm_structured import (
    OpenAIProvider,
    StructuredLLMProvider,
    StructuredProviderError,
    call_openai_structured,
    get_llm_provider,
    set_llm_provider,
)


class ExampleOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str


@pytest.fixture(autouse=True)
def _reset_provider_singleton():
    """Every test in this file starts and ends with no cached provider, so it doesn't leak
    into other test files that rely on get_llm_provider() lazily building a real OpenAIProvider."""
    set_llm_provider(None)
    yield
    set_llm_provider(None)


class FakeProvider(StructuredLLMProvider):
    """A provider with no OpenAI/HTTP involvement at all — proves callers only depend on the
    StructuredLLMProvider interface, not on any vendor-specific behavior."""

    def __init__(self):
        self.calls = []

    async def complete(self, system, user, schema_model, *, operation, model=None):
        self.calls.append({"system": system, "user": user, "operation": operation, "model": model})
        return schema_model(value=f"handled-by-fake:{operation}")


@pytest.mark.asyncio
async def test_call_openai_structured_delegates_to_whatever_provider_is_active():
    fake = FakeProvider()
    set_llm_provider(fake)

    result = await call_openai_structured("sys", "usr", ExampleOutput, operation="job_matching")

    assert result.value == "handled-by-fake:job_matching"
    assert fake.calls == [{"system": "sys", "user": "usr", "operation": "job_matching", "model": None}]


def test_get_llm_provider_defaults_to_openai(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    provider = get_llm_provider()

    assert isinstance(provider, OpenAIProvider)


def test_get_llm_provider_rejects_unknown_provider_name(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "some-unregistered-vendor")

    with pytest.raises(StructuredProviderError, match="Unknown LLM_PROVIDER"):
        get_llm_provider()


def test_get_llm_provider_caches_the_instance(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    first = get_llm_provider()
    second = get_llm_provider()

    assert first is second
