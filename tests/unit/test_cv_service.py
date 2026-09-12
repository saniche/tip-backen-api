import pytest

from cv_service import validate_cv_selection
from pipeline.cv_tailoring import CV_TAILORING_SYSTEM_PROMPT, TailoredCvOutput, _validate_grounded_content
from pipeline.profile_builder import SkillEntry, UserProfile
from pipeline.llm_matching import JobData


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
    profile = UserProfile(TechnicalSkills=[SkillEntry(Name="Python")])
    job = JobData(title="Engineer", technical_stack=["FastAPI"])

    with pytest.raises(ValueError, match="unsupported skills"):
        _validate_grounded_content(output, profile, job)


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
