import ast
from profile.profile_builder import Education, SkillEntry, UserProfile, WorkExperience

import pytest

import cv.cv_tailoring as cv_tailoring
from cv.cv_service import validate_cv_selection
from cv.cv_tailoring import CV_TAILORING_SYSTEM_PROMPT, TailoredCvOutput, _validate_grounded_content
from matching.llm_matching import JobData


def test_cv_selection_rejects_mixed_owners_and_empty_selection():
    with pytest.raises(ValueError, match="At least one"):
        validate_cv_selection([], "per_job")
    with pytest.raises(ValueError, match="same owner"):
        validate_cv_selection([{"user_id": "one"}, {"user_id": "two"}], "group_all")


def test_cv_selection_accepts_supported_modes():
    assert validate_cv_selection([{"user_id": "one"}], "per_job") is None
    assert validate_cv_selection([{"user_id": "one"}], "group_all") is None


def test_cv_prompt_requires_field_level_evidence():
    for evidence_field in (
        "summary_evidence",
        "experience_evidence",
        "education_evidence",
        "certification_evidence",
    ):
        assert evidence_field in CV_TAILORING_SYSTEM_PROMPT


def test_tailored_cv_rejects_skills_missing_from_profile_and_job():
    output = TailoredCvOutput(
        target_role="Engineer", summary="Summary", experience=[], education=[], certifications=[], skills=["Rust"],
        summary_evidence=[], experience_evidence=[], education_evidence=[], certification_evidence=[],
    )
    profile = UserProfile(Skills=[SkillEntry(Name="Python")])
    job = JobData(title="Engineer", technical_stack=["FastAPI"])

    with pytest.raises(ValueError, match="unsupported skills"):
        _validate_grounded_content(output, profile, job)


def test_cv_grounding_accepts_realisation_descriptions_as_experience_evidence():
    output = TailoredCvOutput(
        target_role="Engineer",
        summary="Python engineer",
        experience=["Delivered a working engine"],
        education=[],
        certifications=[],
        skills=[],
        summary_evidence=["Python engineer"],
        experience_evidence=[["Delivered a working engine"]],
        education_evidence=[],
        certification_evidence=[],
    )
    profile = UserProfile(
        Summary="Python engineer",
        WorkExperiences=[WorkExperience(RealisationDescription=["Delivered a working engine"])],
    )
    job = JobData(title="Engineer")

    _validate_grounded_content(output, profile, job)


def test_cv_grounding_accepts_education_location_and_completion():
    output = TailoredCvOutput(
        target_role="Engineer",
        summary="Python engineer",
        experience=[],
        education=["Completed MSc at University in London"],
        certifications=[],
        skills=[],
        summary_evidence=["Python engineer"],
        experience_evidence=[],
        education_evidence=[["Completed", "MSc", "University", "London"]],
        certification_evidence=[],
    )
    profile = UserProfile(
        Summary="Python engineer",
        Education=[
            Education(Institution="University", Location="London", Degree="MSc", Completed=True)
        ],
    )
    job = JobData(title="Engineer")

    _validate_grounded_content(output, profile, job)


@pytest.mark.asyncio
async def test_cv_context_excludes_fields_selected_as_profile_only(monkeypatch):
    captured = {}

    async def capture_context(system, user, schema_model, **kwargs):
        captured.update(ast.literal_eval(user))
        return schema_model(
            target_role="Engineer",
            summary="Python engineer",
            experience=[],
            education=[],
            certifications=[],
            skills=[],
            summary_evidence=["Python engineer"],
            experience_evidence=[],
            education_evidence=[],
            certification_evidence=[],
        )

    monkeypatch.setattr(cv_tailoring, "call_openai_structured", capture_context)
    profile = UserProfile(
        Summary="Python engineer",
        CoreCompetences=["Technical leadership"],
        AdditionalInformations=["Available for relocation"],
    )

    await cv_tailoring.build_tailored_cv(profile, JobData(title="Engineer"), 80)

    assert "CoreCompetences" not in captured["profile"]
    assert "AdditionalInformations" not in captured["profile"]


@pytest.mark.asyncio
async def test_cv_context_omits_unavailable_matching_score(monkeypatch):
    captured = {}

    async def capture_context(system, user, schema_model, **kwargs):
        captured.update(ast.literal_eval(user))
        return schema_model(
            target_role="Engineer",
            summary="Python engineer",
            experience=[],
            education=[],
            certifications=[],
            skills=[],
            summary_evidence=["Python engineer"],
            experience_evidence=[],
            education_evidence=[],
            certification_evidence=[],
        )

    monkeypatch.setattr(cv_tailoring, "call_openai_structured", capture_context)
    await cv_tailoring.build_tailored_cv(
        UserProfile(Summary="Python engineer"),
        JobData(title="Engineer"),
        None,
    )

    assert "match_score" not in captured


def test_tailored_cv_rejects_unsupported_summary_claims():
    output = TailoredCvOutput(
        target_role="Engineer", summary="Award-winning Rust architect", experience=[], education=[], certifications=[], skills=[],
        summary_evidence=[], experience_evidence=[], education_evidence=[], certification_evidence=[],
    )
    profile = UserProfile(Summary="Python engineer")
    job = JobData(title="Engineer")

    with pytest.raises(ValueError, match="unsupported summary"):
        _validate_grounded_content(output, profile, job)


def test_tailored_cv_rejects_unsupported_combination_of_source_words():
    output = TailoredCvOutput(
        target_role="Engineer", summary="Python engineer architect", experience=[], education=[], certifications=[], skills=[],
        summary_evidence=["Python engineer"], experience_evidence=[], education_evidence=[], certification_evidence=[],
    )
    profile = UserProfile(Summary="Python engineer", PreferredJobTitles=["Architect"])
    job = JobData(title="Engineer")

    with pytest.raises(ValueError, match="unsupported summary content"):
        _validate_grounded_content(output, profile, job)
