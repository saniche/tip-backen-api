import ast

import pytest
from pydantic import ValidationError

import cover_letter.cover_letter_tailoring as module
from candidate_profile.profile_builder import UserProfile
from cover_letter.cover_letter_tailoring import (
    COVER_LETTER_SYSTEM_PROMPT,
    STYLE_REFERENCE_ADDENDUM,
    CoverLetterOutput,
    build_cover_letter,
)
from matching.llm_matching import JobData
from shared.llm_structured import StructuredProviderError

PROFILE = UserProfile(Name="Jane", Summary="Python engineer", WorkExperiences=[])
JOB = JobData(title="Python Engineer", company="Acme", key_responsibilities=["Build APIs"])


def _provider(monkeypatch, outputs):
    calls = []

    async def fake(system, user, schema_model, **kwargs):
        calls.append({"system": system, "context": ast.literal_eval(user)})
        greeting, paragraphs, closing = outputs[min(len(calls) - 1, len(outputs) - 1)]
        return schema_model(greeting=greeting, paragraphs=paragraphs, closing=closing)

    monkeypatch.setattr(module, "call_openai_structured", fake)
    return calls


@pytest.mark.asyncio
async def test_valid_letter_is_returned_without_a_warning(monkeypatch):
    calls = _provider(monkeypatch, [("Dear team,", ["I build APIs with Python at Acme."], "Regards,")])

    letter, warning = await build_cover_letter(PROFILE, JOB)

    assert letter.paragraphs == ["I build APIs with Python at Acme."]
    assert warning is None and len(calls) == 1
    assert "style_reference" not in calls[0]["context"]
    assert STYLE_REFERENCE_ADDENDUM not in calls[0]["system"]


@pytest.mark.asyncio
async def test_invented_facts_are_not_checked_or_retried(monkeypatch):
    calls = _provider(monkeypatch, [("Hi,", ["I led the Google team in 2019."], "Bye,")])

    letter, warning = await build_cover_letter(PROFILE, JOB)

    assert letter.paragraphs == ["I led the Google team in 2019."]
    assert warning is None and len(calls) == 1


@pytest.mark.asyncio
async def test_style_reference_is_sent_with_its_rules_and_length_is_steered(monkeypatch):
    reference = " ".join(["word"] * 100)
    long_body = " ".join(["delivery"] * 96)
    calls = _provider(monkeypatch, [("Hi,", ["Short note."], "Bye,"), ("Hi,", [long_body], "Bye,")])

    letter, warning = await build_cover_letter(PROFILE, JOB, style_reference=reference)

    assert len(calls) == 2
    assert calls[0]["context"]["style_reference"] == reference
    assert STYLE_REFERENCE_ADDENDUM in calls[0]["system"] and COVER_LETTER_SYSTEM_PROMPT in calls[0]["system"]
    assert "off-style" in calls[1]["context"]["validation_feedback"]
    assert warning is None and letter.paragraphs == [long_body]


@pytest.mark.asyncio
async def test_letter_that_stays_off_style_is_kept_with_a_warning(monkeypatch):
    calls = _provider(monkeypatch, [("Hi,", ["Short note."], "Bye,")])

    letter, warning = await build_cover_letter(PROFILE, JOB, style_reference=" ".join(["word"] * 100))

    assert letter.paragraphs == ["Short note."]
    assert "words" in warning and len(calls) == 2
    assert "off-style" in calls[1]["context"]["validation_feedback"]


def test_cover_letter_output_schema_remains_unchanged():
    schema = CoverLetterOutput.model_json_schema()
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["greeting", "paragraphs", "closing"]
    assert schema["properties"] == {
        "greeting": {"minLength": 1, "title": "Greeting", "type": "string"},
        "paragraphs": {
            "items": {"type": "string"}, "maxItems": 6, "minItems": 1, "title": "Paragraphs", "type": "array"
        },
        "closing": {"minLength": 1, "title": "Closing", "type": "string"},
    }
    with pytest.raises(ValidationError):
        CoverLetterOutput(greeting="Hi", paragraphs=[], closing="Bye")
    with pytest.raises(ValidationError):
        CoverLetterOutput(greeting="Hi", paragraphs=["Body"], closing="Bye", extra="unexpected")


@pytest.mark.asyncio
async def test_short_reference_does_not_trigger_retry_and_is_truncated(monkeypatch):
    calls = _provider(monkeypatch, [("Hi,", ["Short note."], "Bye,")])
    _, warning = await build_cover_letter(PROFILE, JOB, style_reference="x" * 7000)
    assert len(calls) == 1 and warning is None
    assert len(calls[0]["context"]["style_reference"]) == module.MAX_STYLE_REFERENCE_CHARS


@pytest.mark.asyncio
async def test_provider_error_is_not_swallowed(monkeypatch):
    async def fail(*args, **kwargs):
        raise StructuredProviderError("unavailable")

    monkeypatch.setattr(module, "call_openai_structured", fail)
    with pytest.raises(StructuredProviderError, match="unavailable"):
        await build_cover_letter(PROFILE, JOB)
