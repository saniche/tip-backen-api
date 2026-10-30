import json
from profile.profile_builder import Education, UserProfile, WorkExperience

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
        "description_evidence",
        "education_evidence",
        "certification_evidence",
    ):
        assert evidence_field in CV_TAILORING_SYSTEM_PROMPT
    assert "summary_evidence" not in CV_TAILORING_SYSTEM_PROMPT
    assert "summary_evidence" not in TailoredCvOutput.model_fields


def _output_with_skills(skills):
    return TailoredCvOutput(
        target_role="Engineer",
        summary="Python engineer",
        experience=[],
        education=[],
        certifications=[],
        skills=skills,
        education_evidence=[],
        certification_evidence=[],
    )


@pytest.mark.parametrize("skill", ["Patient assessment", "Inventory management", "FastAPI"])
def test_cv_does_not_reject_skills_based_on_profile_matching(skill):
    profile = UserProfile(Summary="Professional")
    output = _output_with_skills([skill])

    _validate_grounded_content(output, profile, JobData(title="Engineer", tools_and_technologies=["FastAPI"]))


def _structured_experience(**overrides):
    item = {
        "profile_index": 0,
        "title": "Community Care Lead",
        "company": "Care Hospital",
        "start_date": "2020",
        "end_date": "2023",
        "descriptions": ["Delivered patient care"],
        "description_evidence": [["Delivered patient care"]],
    }
    item.update(overrides)
    return item


def _profile_with_experience():
    return UserProfile(WorkExperiences=[
        WorkExperience(
            Title="Nurse", Company="Care Hospital", StartDate="2020", EndDate="2023",
            RealisationDescription=["Delivered patient care"],
        ),
        WorkExperience(Title="Nurse", Company="Other Hospital", StartDate="2010", EndDate="2015"),
    ])


def _output_with_experience(item):
    return TailoredCvOutput(
        target_role="Engineer",
        summary="Summary",
        experience=[item],
        education=[],
        certifications=[],
        skills=[],
        education_evidence=[],
        certification_evidence=[],
    )


def test_experience_accepts_tailored_title_with_matching_company_and_dates():
    _validate_grounded_content(
        _output_with_experience(_structured_experience()), _profile_with_experience(), JobData(title="Engineer")
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("source_summary", "realisations"),
    [
        ("Provided patient care", None),
        (None, ["Delivered patient care"]),
        ("Provided patient care", ["Delivered patient care"]),
    ],
)
async def test_experience_optional_summary_uses_available_profile_details(monkeypatch, source_summary, realisations):
    profile = UserProfile(WorkExperiences=[WorkExperience(
        Title="Nurse", Summary=source_summary, RealisationDescription=realisations,
    )])
    contexts = []

    async def provider(system, user, schema_model, **kwargs):
        contexts.append(json.loads(user))
        return _output_with_experience(_structured_experience(
            company=None, start_date=None, end_date=None, summary="Supported patient care.",
            descriptions=[], description_evidence=[],
        ))

    monkeypatch.setattr(cv_tailoring, "call_openai_structured", provider)
    result = await cv_tailoring.build_tailored_cv(profile, JobData(title="Engineer"), None)

    assert result.experience == ["Community Care Lead", "Supported patient care."]
    assert contexts[0]["profile"]["WorkExperiences"][0]["Summary"] == source_summary
    assert contexts[0]["profile"]["WorkExperiences"][0]["RealisationDescription"] == realisations


@pytest.mark.asyncio
async def test_experience_without_responsibility_details_keeps_header(monkeypatch):
    profile = UserProfile(WorkExperiences=[WorkExperience(Title="Nurse", Company="Care Hospital")])

    async def provider(system, user, schema_model, **kwargs):
        return _output_with_experience(_structured_experience(
            start_date=None, end_date=None, summary=None, descriptions=[], description_evidence=[],
        ))

    monkeypatch.setattr(cv_tailoring, "call_openai_structured", provider)
    result = await cv_tailoring.build_tailored_cv(profile, JobData(title="Engineer"), None)

    assert result.experience == ["Community Care Lead | Care Hospital"]


def test_experience_summary_is_not_evidence_checked():
    item = _structured_experience(summary="A freely tailored summary.")

    _validate_grounded_content(_output_with_experience(item), _profile_with_experience(), JobData(title="Engineer"))


@pytest.mark.parametrize(("summary", "descriptions", "evidence"), [
    ("Invented summary.", [], []),
    (None, ["Care Hospital"], [["Care Hospital"]]),
])
def test_experience_without_responsibility_details_rejects_generated_narrative(summary, descriptions, evidence):
    profile = UserProfile(WorkExperiences=[WorkExperience(Title="Nurse", Company="Care Hospital")])
    output = _output_with_experience(_structured_experience(
        start_date=None, end_date=None, summary=summary, descriptions=descriptions, description_evidence=evidence,
    ))

    with pytest.raises(ValueError, match="no responsibility details"):
        _validate_grounded_content(output, profile, JobData(title="Engineer"))


@pytest.mark.asyncio
@pytest.mark.parametrize("source", [
    "Consulted for major clients and maintained and modernized software products.",
    "Improved patient's care\nà Montréal.",
])
async def test_experience_uses_json_context_and_accepts_exact_field_representation(monkeypatch, source):
    profile = UserProfile(WorkExperiences=[WorkExperience(Summary=source)])
    calls = []

    async def provider(system, user, schema_model, **kwargs):
        context = json.loads(user)
        calls.append(context)
        assert context["profile"]["WorkExperiences"][0]["Summary"] == source
        assert context["profile"]["WorkExperiences"][0]["Company"] is None
        return _output_with_experience(_structured_experience(
            company=None, start_date=None, end_date=None, descriptions=[source],
            description_evidence=[[f"Summary={source!r}"]],
        ))

    monkeypatch.setattr(cv_tailoring, "call_openai_structured", provider)
    result = await cv_tailoring.build_tailored_cv(profile, JobData(title="Engineer"), None)

    assert len(calls) == 1
    assert source in result.experience


@pytest.mark.parametrize("citation", [
    "Summary='Invented experience'",
    "Title='Provided patient care'",
])
def test_experience_rejects_mismatched_field_representation(citation):
    profile = UserProfile(WorkExperiences=[WorkExperience(Summary="Provided patient care")])
    output = _output_with_experience(_structured_experience(
        company=None, start_date=None, end_date=None, descriptions=["Provided patient care"],
        description_evidence=[[citation]],
    ))

    with pytest.raises(ValueError, match="unsupported"):
        _validate_grounded_content(output, profile, JobData(title="Engineer"))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("company", "Other Hospital"),
        ("company", "Invented Hospital"),
        ("start_date", "2010"),
        ("end_date", "2024"),
    ],
)
def test_experience_rejects_company_and_dates_not_matching_linked_profile(field, value):
    with pytest.raises(ValueError) as error:
        _validate_grounded_content(
            _output_with_experience(_structured_experience(**{field: value})),
            _profile_with_experience(), JobData(title="Engineer"),
        )
    assert field in str(error.value)
    assert value in str(error.value)


@pytest.mark.parametrize("index", [-1, 2])
def test_experience_rejects_invalid_profile_index(index):
    with pytest.raises(ValueError, match="profile_index"):
        _validate_grounded_content(
            _output_with_experience(_structured_experience(profile_index=index)),
            _profile_with_experience(), JobData(title="Engineer"),
        )


@pytest.mark.parametrize(
    ("descriptions", "evidence", "reason"),
    [
        (["Delivered patient care"], [[]], "no evidence provided"),
        (["Delivered patient care"], [["patient care"]], "patient care"),
        (["Managed patient care"], [["Delivered patient care"]], "Managed"),
        (["Delivered patient care"], [], "1 items, 0 evidence lists"),
    ],
)
def test_experience_rejects_unsupported_description_with_details(descriptions, evidence, reason):
    with pytest.raises(ValueError) as error:
        _validate_grounded_content(
            _output_with_experience(_structured_experience(
                descriptions=descriptions, description_evidence=evidence
            )),
            _profile_with_experience(), JobData(title="Engineer"),
        )
    assert reason in str(error.value)


def test_experience_accepts_absent_company_and_dates_if_profile_omits_them():
    item = _structured_experience(company=None, start_date=None, end_date=None)
    profile = UserProfile(WorkExperiences=[WorkExperience(RealisationDescription=["Delivered patient care"])])

    _validate_grounded_content(_output_with_experience(item), profile, JobData(title="Engineer"))


@pytest.mark.asyncio
async def test_experience_retry_receives_details_and_renders_valid_fields(monkeypatch):
    calls = []

    async def provider(system, user, schema_model, **kwargs):
        calls.append(user)
        item = _structured_experience(company="Wrong Hospital") if len(calls) == 1 else _structured_experience()
        return _output_with_experience(item)

    monkeypatch.setattr(cv_tailoring, "call_openai_structured", provider)
    result = await cv_tailoring.build_tailored_cv(_profile_with_experience(), JobData(title="Engineer"), None)

    assert len(calls) == 2
    assert "Wrong Hospital" in calls[1]
    assert "company" in calls[1]
    assert result.experience == [
        "Community Care Lead | Care Hospital | 2020 - 2023",
        "Delivered patient care",
    ]


def test_cv_grounding_accepts_realisation_descriptions_as_experience_evidence():
    output = _output_with_experience(
        _structured_experience(
            company=None, start_date=None, end_date=None,
            descriptions=["Delivered a working engine"],
            description_evidence=[["Delivered a working engine"]],
        )
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
        captured.update(json.loads(user))
        return schema_model(
            target_role="Engineer",
            summary="Python engineer",
            experience=[],
            education=[],
            certifications=[],
            skills=[],
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
        captured.update(json.loads(user))
        return schema_model(
            target_role="Engineer",
            summary="Python engineer",
            experience=[],
            education=[],
            certifications=[],
            skills=[],
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


@pytest.mark.asyncio
async def test_tailored_cv_summary_does_not_require_grounding_or_evidence(monkeypatch):
    calls = []

    async def provider(system, user, schema_model, **kwargs):
        calls.append(user)
        output = _output_with_skills([])
        output.summary = "Award-winning Rust architect"
        return output

    monkeypatch.setattr(cv_tailoring, "call_openai_structured", provider)
    result = await cv_tailoring.build_tailored_cv(UserProfile(Summary="Python engineer"), JobData(title="Engineer"), None)

    assert result.summary == "Award-winning Rust architect"
    assert len(calls) == 1


@pytest.mark.parametrize(
    ("section", "evidence_field"),
    [
        ("education", "education_evidence"),
        ("certifications", "certification_evidence"),
    ],
)
def test_non_summary_sections_still_require_supported_evidence(section, evidence_field):
    output = _output_with_skills([])
    setattr(output, section, ["Invented claim"])
    setattr(output, evidence_field, [["Invented claim"]])

    with pytest.raises(ValueError, match="unsupported"):
        _validate_grounded_content(output, UserProfile(Summary="Python engineer"), JobData(title="Engineer"))
