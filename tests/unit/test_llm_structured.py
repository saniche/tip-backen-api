import logging

import pytest
from openai import OpenAIError
from pydantic import BaseModel, ConfigDict

import shared.config as config
import shared.llm_structured as llm_structured
from shared.llm_structured import StructuredProviderError, call_openai_structured


class ExampleOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str


@pytest.mark.asyncio
async def test_structured_call_uses_operation_model_and_validates_response(monkeypatch):
    captured = {}

    class Response:
        output_parsed = ExampleOutput(value="valid")

    class Client:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.responses = self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def parse(self, **kwargs):
            captured["request"] = kwargs
            return Response()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(llm_structured, "AsyncOpenAI", Client)

    result = await call_openai_structured("system", "user", ExampleOutput, operation="job_matching")

    assert result.value == "valid"
    assert captured["client"] == {"api_key": "test-key", "timeout": llm_structured.OPENAI_TIMEOUT_SECONDS}
    assert captured["request"]["model"] == llm_structured.OPENAI_MODELS["job_matching"]
    assert captured["request"]["instructions"] == "system"
    assert captured["request"]["input"] == "user"
    assert captured["request"]["text_format"] is ExampleOutput
    assert captured["request"]["reasoning"] == {"effort": llm_structured.OPENAI_REASONING_EFFORT}
    assert "temperature" not in captured["request"]


def test_reasoning_effort_defaults_to_medium(monkeypatch):
    monkeypatch.delenv("OPENAI_REASONING_EFFORT", raising=False)

    assert config._get_reasoning_effort() == "medium"


def test_reasoning_effort_rejects_invalid_configuration(monkeypatch):
    monkeypatch.setenv("OPENAI_REASONING_EFFORT", "extreme")

    with pytest.raises(ValueError, match="OPENAI_REASONING_EFFORT must be one of"):
        config._get_reasoning_effort()


@pytest.mark.asyncio
async def test_structured_call_rejects_missing_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(StructuredProviderError, match="not configured"):
        await call_openai_structured("system", "user", ExampleOutput, operation="profile_builder")


@pytest.mark.asyncio
async def test_structured_call_translates_invalid_output(monkeypatch):
    class Response:
        output_parsed = None

    class Client:
        def __init__(self, **kwargs):
            self.responses = self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def parse(self, **kwargs):
            return Response()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(llm_structured, "AsyncOpenAI", Client)

    with pytest.raises(StructuredProviderError, match="did not return a usable result"):
        await call_openai_structured("system", "user", ExampleOutput, operation="profile_builder")


@pytest.mark.asyncio
async def test_structured_call_translates_openai_sdk_errors(monkeypatch, caplog):
    class OpenAIRequestError(OpenAIError):
        status_code = 401
        request_id = "req_test"
        code = "invalid_api_key"
        param = None
        type = "authentication_error"

    class Client:
        def __init__(self, **kwargs):
            self.responses = self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def parse(self, **kwargs):
            raise OpenAIRequestError("sensitive provider body")

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(llm_structured, "AsyncOpenAI", Client)
    caplog.set_level(logging.WARNING, logger="tip-api")

    with pytest.raises(StructuredProviderError, match="External processing failed"):
        await call_openai_structured("system", "user", ExampleOutput, operation="profile_builder")

    record = next(record for record in caplog.records if record.message.startswith("Structured provider failed"))
    assert record.error_type == "OpenAIRequestError"
    assert record.openai_status_code == 401
    assert record.openai_request_id == "req_test"
    assert record.openai_code == "invalid_api_key"
    assert record.openai_type == "authentication_error"
    assert "openai_status_code=401" in record.message
    assert "openai_code=invalid_api_key" in record.message
    assert "sensitive provider body" not in caplog.text


@pytest.mark.asyncio
async def test_structured_call_logs_only_operation_metadata(monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="tip-api")

    class Response:
        output_parsed = ExampleOutput(value="valid")

    class Client:
        def __init__(self, **kwargs):
            self.responses = self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def parse(self, **kwargs):
            return Response()

    monkeypatch.setenv("OPENAI_API_KEY", "secret-key")
    monkeypatch.setattr(llm_structured, "AsyncOpenAI", Client)

    await call_openai_structured("system", "candidate sensitive resume", ExampleOutput, operation="job_normalizer")

    record = next(record for record in caplog.records if record.message == "Structured provider completed")
    assert record.operation == "job_normalizer"
    assert record.model == llm_structured.OPENAI_MODELS["job_normalizer"]
    assert isinstance(record.duration_ms, int)
    assert "secret-key" not in caplog.text
    assert "candidate sensitive resume" not in caplog.text