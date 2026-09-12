import pytest

from llm_structured import StructuredProviderError
from pipeline.job_matching import build_match_result
from pipeline.llm_matching import JobData, LlmMatchOutput, StructuredMatchOutput, get_llm_match_output


def test_build_match_result_scores_and_marks_eligible():
    output = LlmMatchOutput(
        required_qualifications=[{"result": "Yes", "value": "Bachelor's degree"}],
        required_skills=[{"result": "Yes", "value": "Python"}, {"result": "Partial", "value": "SQL"}],
        desirable_skills=[{"result": "Yes", "value": "FastAPI"}],
        technical_stack=[{"result": "Partial", "value": "PostgreSQL"}],
    )

    result = build_match_result(output)

    assert result.score >= 0
    assert result.eligible is True
    assert result.scoring_status == "scored"
    assert "required_skills" in result.breakdown


@pytest.mark.asyncio
async def test_matching_rejects_incomplete_requirement_assessments(monkeypatch):
    import pipeline.llm_matching as llm_matching

    async def fake_call(*args, **kwargs):
        return StructuredMatchOutput(
            required_qualifications=[], required_skills=[], desirable_qualifications=[], desirable_skills=[],
            technical_stack=[], notes="No evidence found.",
        )

    monkeypatch.setattr(llm_matching, "call_openai_structured", fake_call)
    with pytest.raises(StructuredProviderError, match="does not cover required_skills"):
        await get_llm_match_output(
            {"skills": []}, JobData(required={"qualifications": [], "skills": ["Python"]}, desirable={})
        )


@pytest.mark.asyncio
async def test_matching_rejects_duplicate_requirement_assessments(monkeypatch):
    import pipeline.llm_matching as llm_matching

    async def fake_call(*args, **kwargs):
        assessment = {"result": "Yes", "value": "Python", "rationale": "Profile contains Python."}
        return StructuredMatchOutput(
            required_qualifications=[], required_skills=[assessment, assessment], desirable_qualifications=[],
            desirable_skills=[], technical_stack=[], notes="No evidence found.",
        )

    monkeypatch.setattr(llm_matching, "call_openai_structured", fake_call)
    with pytest.raises(StructuredProviderError, match="does not cover required_skills"):
        await get_llm_match_output(
            {"skills": ["Python"]}, JobData(required={"qualifications": [], "skills": ["Python"]}, desirable={})
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("result", ["Yes", "Partial"])
async def test_matching_rejects_positive_assessment_without_profile_evidence(monkeypatch, result):
    import pipeline.llm_matching as llm_matching

    async def fake_call(*args, **kwargs):
        return StructuredMatchOutput(
            required_qualifications=[],
            required_skills=[{"result": result, "value": "Python", "rationale": "Profile contains Python."}],
            desirable_qualifications=[],
            desirable_skills=[],
            technical_stack=[],
            notes="Validated profile-to-job comparison.",
        )

    monkeypatch.setattr(llm_matching, "call_openai_structured", fake_call)
    with pytest.raises(StructuredProviderError, match="profile evidence"):
        await get_llm_match_output(
            {"skills": ["Java"]}, JobData(required={"qualifications": [], "skills": ["Python"]}, desirable={})
        )
