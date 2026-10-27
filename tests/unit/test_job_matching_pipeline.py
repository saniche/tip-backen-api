import json

import pytest
from pydantic import ValidationError

from matching.job_matching import build_match_result
from matching.llm_matching import (
    ItemMatching,
    JobData,
    LlmMatchOutput,
    MatchAnalysis,
    get_llm_match_output,
    matching_criteria,
)
from shared.llm_structured import StructuredProviderError


def item(criterion: str, judgment: str = "Yes", evidence: str | None = None) -> dict:
    return {
        "criterion": criterion,
        "judgment": judgment,
        "evidence": evidence or f"The profile supports {criterion}.",
    }


def output(
    requirements: list[dict] | None = None,
    desirables: list[dict] | None = None,
    **extra,
) -> LlmMatchOutput:
    payload = {
        "requirements": requirements or [],
        "desirables": desirables or [],
        "notes": "Evidence was assessed against the supplied profile.",
        "analysis": {
            "eligibility": "Mandatory evidence remains subject to verification.",
            "matching": "The profile aligns with the supplied criteria.",
            "chance_of_success": "Hiring outcomes remain uncertain.",
        },
        **extra,
    }
    return LlmMatchOutput.model_validate(payload)


@pytest.mark.parametrize("judgment", ["Yes", "No"])
def test_binary_judgments_accept_only_exact_values(judgment):
    assert ItemMatching(criterion="Python", judgment=judgment, evidence="The profile mentions Python.").judgment == judgment


@pytest.mark.parametrize("judgment", ["Partial", "Unknown", "yes", "NO", None, 1])
def test_binary_judgments_reject_other_values(judgment):
    with pytest.raises(ValidationError):
        ItemMatching(criterion="Python", judgment=judgment, evidence="Evidence.")


def test_output_models_forbid_extra_fields_and_require_all_fields():
    valid = output().model_dump()
    with pytest.raises(ValidationError):
        LlmMatchOutput.model_validate({**valid, "score": 100})
    with pytest.raises(ValidationError):
        ItemMatching(criterion="Python", judgment="Yes", evidence="Present.", legacy="value")
    with pytest.raises(ValidationError):
        MatchAnalysis(eligibility="Enough", matching="Enough", chance_of_success="Uncertain", score=95)
    with pytest.raises(ValidationError):
        LlmMatchOutput.model_validate({"requirements": [], "desirables": [], "notes": "Present."})


@pytest.mark.parametrize(
    "payload",
    [
        {"criterion": " ", "judgment": "Yes", "evidence": "Evidence."},
        {"criterion": "Python", "judgment": "Yes", "evidence": "\t"},
    ],
)
def test_criterion_and_evidence_must_be_non_empty(payload):
    with pytest.raises(ValidationError):
        ItemMatching.model_validate(payload)


@pytest.mark.parametrize("field", ["eligibility", "matching", "chance_of_success"])
def test_analysis_fields_must_be_non_empty(field):
    analysis = {
        "eligibility": "Assessment.",
        "matching": "Assessment.",
        "chance_of_success": "Assessment.",
    }
    analysis[field] = "  "
    with pytest.raises(ValidationError):
        MatchAnalysis.model_validate(analysis)


def test_notes_must_be_non_empty():
    with pytest.raises(ValidationError):
        output(notes=" ")


@pytest.mark.parametrize("raw", ["{bad json", "```json\n{}\n```", "Here is the result: {}"])
def test_non_json_or_markdown_wrapped_output_is_rejected(raw):
    with pytest.raises(ValidationError):
        LlmMatchOutput.model_validate_json(raw)


@pytest.mark.asyncio
async def test_matching_rejects_category_without_any_assessment(monkeypatch):
    import matching.llm_matching as llm_matching

    async def fake_call(*args, **kwargs):
        return output([], [])

    monkeypatch.setattr(llm_matching, "call_openai_structured", fake_call)
    with pytest.raises(StructuredProviderError, match="requirements"):
        await get_llm_match_output(
            {"skills": ["Python", "SQL"]},
            JobData(required={"qualifications": [], "skills": ["Python", "SQL"]}, desirable={}),
        )


@pytest.mark.asyncio
async def test_matching_accepts_split_criteria(monkeypatch):
    import matching.llm_matching as llm_matching

    async def fake_call(*args, **kwargs):
        return output([item("Python"), item("SQL"), item("Docker")])

    monkeypatch.setattr(llm_matching, "call_openai_structured", fake_call)
    result = await get_llm_match_output(
        {"skills": ["Python"]},
        JobData(required={"qualifications": [], "skills": ["Python", "SQL and Docker"]}, desirable={}),
    )

    assert len(result.requirements) == 3


@pytest.mark.asyncio
async def test_matching_preserves_duplicate_criteria_at_each_position(monkeypatch):
    import matching.llm_matching as llm_matching

    async def fake_call(*args, **kwargs):
        return output([item("Python"), item("Python")])

    monkeypatch.setattr(llm_matching, "call_openai_structured", fake_call)
    result = await get_llm_match_output(
        {"skills": ["Python"]},
        JobData(required={"qualifications": [], "skills": ["Python", "Python"]}, desirable={}),
    )

    assert [assessment.criterion for assessment in result.requirements] == ["Python", "Python"]


def test_matching_adapter_preserves_flat_and_nested_order_and_duplicates():
    criteria = matching_criteria(
        JobData(
            required={"qualifications": ["Degree", "Degree"], "skills": ["Python", "SQL"]},
            desirable=["FastAPI", "FastAPI"],
        )
    )

    assert criteria.requirements == ["Degree", "Degree", "Python", "SQL"]
    assert criteria.desirables == ["FastAPI", "FastAPI"]
    assert criteria.required_qualifications == ["Degree", "Degree"]
    assert criteria.required_skills == ["Python", "SQL"]


def test_build_match_result_uses_new_schema_and_preserves_eligibility():
    job = JobData(
        required={"qualifications": ["Degree"], "skills": ["Python", "SQL"]},
        desirable={"qualifications": [], "skills": ["FastAPI"]},
    )
    match_output = output(
        [
            item("Degree", "Yes"),
            item("Python", "Yes"),
            item("SQL", "Yes"),
        ],
        [item("FastAPI", "Yes")],
    )

    result = build_match_result(match_output, job)

    assert result.score == 100
    assert result.eligible is True
    assert result.scoring_status == "scored"
    assert set(result.breakdown) == {"requirements", "desirables"}
    assert json.loads(match_output.model_dump_json())["analysis"]["matching"]
