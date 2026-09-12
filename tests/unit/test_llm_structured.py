import logging

import pytest
from pydantic import BaseModel, ConfigDict

import llm_structured
from llm_structured import StructuredProviderError, call_openai_structured


class ExampleOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str


@pytest.mark.asyncio
async def test_structured_call_uses_operation_model_and_validates_response(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": '{"value":"valid"}'}}]}

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, headers, json):
            captured.update({"url": url, "headers": headers, "json": json})
            return Response()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(llm_structured.httpx, "AsyncClient", lambda timeout: Client())

    result = await call_openai_structured("system", "user", ExampleOutput, operation="job_matching")

    assert result.value == "valid"
    assert captured["json"]["model"] == llm_structured.OPENAI_MODELS["job_matching"]
    assert captured["json"]["response_format"]["json_schema"]["strict"] is True


@pytest.mark.asyncio
async def test_structured_call_rejects_missing_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(StructuredProviderError, match="not configured"):
        await call_openai_structured("system", "user", ExampleOutput, operation="profile_builder")


@pytest.mark.asyncio
async def test_structured_call_translates_invalid_output(monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": '{"unexpected":"field"}'}}]}

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, *args, **kwargs):
            return Response()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(llm_structured.httpx, "AsyncClient", lambda timeout: Client())

    with pytest.raises(StructuredProviderError, match="External processing failed"):
        await call_openai_structured("system", "user", ExampleOutput, operation="profile_builder")


@pytest.mark.asyncio
async def test_structured_call_logs_only_operation_metadata(monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="tip-api")

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": '{"value":"valid"}'}}]}

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, *args, **kwargs):
            return Response()

    monkeypatch.setenv("OPENAI_API_KEY", "secret-key")
    monkeypatch.setattr(llm_structured.httpx, "AsyncClient", lambda timeout: Client())

    await call_openai_structured("system", "candidate sensitive resume", ExampleOutput, operation="job_normalizer")

    record = next(record for record in caplog.records if record.message == "Structured provider completed")
    assert record.operation == "job_normalizer"
    assert record.model == llm_structured.OPENAI_MODELS["job_normalizer"]
    assert isinstance(record.duration_ms, int)
    assert "secret-key" not in caplog.text
    assert "candidate sensitive resume" not in caplog.text