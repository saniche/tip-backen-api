import ast
from profile.profile_builder import UserProfile

import pytest

import cover_letter.cover_letter_tailoring as module
from cover_letter.cover_letter_tailoring import (
    COVER_LETTER_SYSTEM_PROMPT,
    STYLE_REFERENCE_ADDENDUM,
    CoverLetterGroundingError,
    build_cover_letter,
)
from matching.llm_matching import JobData

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
async def test_invented_facts_trigger_one_retry_with_feedback_then_fail(monkeypatch):
    calls = _provider(monkeypatch, [("Hi,", ["I led the Google team in 2019."], "Bye,")])

    with pytest.raises(CoverLetterGroundingError, match="unsupported facts"):
        await build_cover_letter(PROFILE, JOB)

    assert len(calls) == 2
    assert "validation_feedback" in calls[1]["context"]


@pytest.mark.asyncio
async def test_retry_can_recover(monkeypatch):
    calls = _provider(
        monkeypatch,
        [("Hi,", ["I worked at Google."], "Bye,"), ("Hi,", ["I build APIs with Python."], "Bye,")],
    )

    letter, _ = await build_cover_letter(PROFILE, JOB)

    assert letter.paragraphs == ["I build APIs with Python."] and len(calls) == 2


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
    _provider(monkeypatch, [("Hi,", ["Short note."], "Bye,")])

    letter, warning = await build_cover_letter(PROFILE, JOB, style_reference=" ".join(["word"] * 100))

    assert letter.paragraphs == ["Short note."]
    assert "words" in warning
