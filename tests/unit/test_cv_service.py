import json
import logging

import pytest
from openai.lib._pydantic import to_strict_json_schema
from pydantic import ValidationError

import cv.cv_tailoring as module
from candidate_profile.profile_builder import Education, UserProfile, WorkExperience
from cv.cv_service import validate_cv_selection
from cv.cv_tailoring import EmptyExperienceError, TailoredCvOutput, TailoredEducationOutput, TailoredExperienceOutput
from cv.markdown_writer import render_tailored_cv_markdown
from matching.llm_matching import JobData
from shared.llm_structured import StructuredProviderError

JOB = JobData(title="Engineer")


def profile():
    return UserProfile(
        Summary="Professional",
        WorkExperiences=[
            WorkExperience(Company="Café Group", Location="Paris", Title="Developer", StartDate="2020", EndDate=None),
            WorkExperience(Company="Other", Title="Engineer", StartDate="2010", EndDate="2019"),
        ],
        Education=[
            Education(Degree="Maîtrise", Institution="Université", Year="2020", Field="Secret field", Location="Paris"),
            Education(Degree="BSc", Institution="College", Year="2016"),
        ],
    )


def experience(index=0, **changes):
    item = {
        "profile_index": index,
        "title": "Tailored title",
        "company": "Café Group",
        "start_date": "2020",
        "end_date": None,
        "summary": "A reworded summary.",
        "descriptions": ["A reworded achievement."],
    }
    return {**item, **changes}


def education(index=0, **changes):
    return {**{"profile_index": index, "degree": "Maîtrise", "institution": "Université", "year": "2020"}, **changes}


def output(**changes):
    values = {
        "target_role": "generated title",
        "summary": "A reworded overall summary",
        "experience": [experience()],
        "education": [education()],
        "certifications": ["Tailored certificate"],
        "skills": ["Reworded skill"],
    }
    return TailoredCvOutput(**{**values, **changes})


def provider(monkeypatch, outputs):
    calls = []

    async def fake(system, user, schema_model, **kwargs):
        calls.append((system, json.loads(user)))
        return outputs[min(len(calls) - 1, len(outputs) - 1)]

    monkeypatch.setattr(module, "call_openai_structured", fake)
    return calls


def test_cv_selection_rejects_mixed_owners_and_empty_selection():
    with pytest.raises(ValueError, match="At least one"):
        validate_cv_selection([], "per_job")
    with pytest.raises(ValueError, match="same owner"):
        validate_cv_selection([{"user_id": "one"}, {"user_id": "two"}], "group_all")
    assert validate_cv_selection([{"user_id": "one"}], "per_job") is None
    assert validate_cv_selection([{"user_id": "one"}], "group_all") is None


def test_schema_has_nullable_index_and_no_evidence_fields():
    schema = to_strict_json_schema(TailoredCvOutput)
    for model in (TailoredExperienceOutput, TailoredEducationOutput):
        strict = to_strict_json_schema(model)
        assert "profile_index" in strict["required"]
        assert {"type": "null"} in strict["properties"]["profile_index"]["anyOf"]
        assert model.model_validate({**({"title": "", "company": None, "start_date": None, "end_date": None,
                                          "descriptions": []} if model is TailoredExperienceOutput else
                                         {"degree": None, "institution": None, "year": None})}).profile_index is None
    assert "evidence" not in json.dumps(schema)
    assert "description_evidence" not in module.CV_TAILORING_SYSTEM_PROMPT
    with pytest.raises(ValidationError):
        TailoredExperienceOutput(**experience(True))


@pytest.mark.asyncio
async def test_rewording_is_accepted_and_all_objective_fields_are_reconciled(monkeypatch, caplog):
    generated = output(
        experience=[experience(company="Wrong", start_date="1999", end_date="Present")],
        education=[education(degree="Wrong degree", institution="Wrong university", year="1999")],
    )
    calls = provider(monkeypatch, [generated])
    with caplog.at_level(logging.WARNING, logger="tip-api"):
        cv = await module.build_tailored_cv(profile(), JOB, 80)
    assert len(calls) == 1
    assert cv.target_role == "Engineer"
    assert (cv.experience[0].company, cv.experience[0].start_date, cv.experience[0].end_date) == (
        "Café Group", "2020", None
    )
    assert cv.experience[0].title == "Tailored title"
    assert cv.experience[0].summary == "A reworded summary."
    assert cv.experience[0].descriptions == ["A reworded achievement."]
    assert cv.education == ["Maîtrise, Université, 2020"]
    assert cv.skills == ["Reworded skill"] and cv.certifications == ["Tailored certificate"]
    assert len(caplog.records) == 6
    assert "Wrong" not in caplog.text and "Café" not in caplog.text
    rendered = render_tailored_cv_markdown(cv)
    assert "## Engineer" in rendered and "Maîtrise, Université, 2020" in rendered
    assert "Secret field" not in rendered and "Wrong" not in rendered


@pytest.mark.asyncio
async def test_warning_comparison_normalizes_text_but_compares_year_exactly(monkeypatch, caplog):
    calls = provider(monkeypatch, [output(
        experience=[experience(company="  CAFE   GROUP ", start_date=" 2020 ", end_date=None)],
        education=[education(degree="maitrise", institution=" UNIVERSITE ", year=" 2020 ")],
    )])
    with caplog.at_level(logging.WARNING, logger="tip-api"):
        cv = await module.build_tailored_cv(profile(), JOB, None)
    assert len(calls) == 1
    assert cv.experience[0].company == "Café Group"
    assert cv.education == ["Maîtrise, Université, 2020"]
    assert len(caplog.records) == 1 and "year" in caplog.text


@pytest.mark.asyncio
async def test_order_duplicates_and_omissions(monkeypatch, caplog):
    exp2 = experience(1, company="Other", start_date="2010", end_date="2019")
    edu2 = education(1, degree="BSc", institution="College", year="2016")
    calls = provider(monkeypatch, [output(experience=[exp2, experience(), exp2], education=[edu2, education(), edu2])])
    with caplog.at_level(logging.WARNING, logger="tip-api"):
        cv = await module.build_tailored_cv(profile(), JOB, None)
    assert len(calls) == 1
    assert [item.company for item in cv.experience] == ["Other", "Café Group"]
    assert cv.education == ["BSc, College, 2016", "Maîtrise, Université, 2020"]
    assert caplog.text.count("duplicate") == 2
    caplog.clear()
    provider(monkeypatch, [output()])
    await module.build_tailored_cv(profile(), JOB, None)
    assert not caplog.records


@pytest.mark.asyncio
@pytest.mark.parametrize("section", ["experience", "education"])
@pytest.mark.parametrize("index", [None, -1, 2])
@pytest.mark.parametrize("recover", [True, False])
async def test_invalid_indexes_retry_then_recover_or_drop(monkeypatch, caplog, section, index, recover):
    bad = experience(index) if section == "experience" else education(index)
    valid = experience() if section == "experience" else education()
    first = output(**{section: [bad, valid]})
    second = output(**{section: [valid] if recover else [bad, valid]})
    calls = provider(monkeypatch, [first, second])
    with caplog.at_level(logging.WARNING, logger="tip-api"):
        cv = await module.build_tailored_cv(profile(), JOB, None)
    assert len(calls) == 2 and section in calls[1][1]["validation_feedback"]
    assert len(getattr(cv, section)) == 1
    assert ("invalid profile index" in caplog.text) is not recover


@pytest.mark.asyncio
@pytest.mark.parametrize("section", ["experience", "education"])
async def test_missing_index_is_retryable_and_empty_source_is_invalid(monkeypatch, section, caplog):
    item = experience() if section == "experience" else education()
    del item["profile_index"]
    first = output(**{section: [item]})
    source = profile()
    if section == "education":
        source.Education = []
        second = output(education=[education()])
    else:
        source.WorkExperiences = []
        second = output(experience=[experience()])
    calls = provider(monkeypatch, [first, second])
    with caplog.at_level(logging.WARNING, logger="tip-api"):
        if section == "experience":
            with pytest.raises(EmptyExperienceError):
                await module.build_tailored_cv(source, JOB, None)
        else:
            cv = await module.build_tailored_cv(source, JOB, None)
            assert cv.education == [] and "no education" in caplog.text
    assert len(calls) == 2 and "profile_index" in calls[1][1]["validation_feedback"]


@pytest.mark.asyncio
async def test_empty_sections_fail_experience_and_warn_education(monkeypatch, caplog):
    calls = provider(monkeypatch, [output(experience=[])])
    with pytest.raises(EmptyExperienceError):
        await module.build_tailored_cv(profile(), JOB, None)
    assert len(calls) == 1
    calls = provider(monkeypatch, [output(education=[])])
    with caplog.at_level(logging.WARNING, logger="tip-api"):
        cv = await module.build_tailored_cv(profile(), JOB, None)
    assert len(calls) == 1 and cv.education == [] and "no education" in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("section", ["experience", "education"])
async def test_all_invalid_entries_are_dropped_after_retry(monkeypatch, caplog, section):
    bad = experience(-1) if section == "experience" else education(-1)
    calls = provider(monkeypatch, [output(**{section: [bad]})])
    with caplog.at_level(logging.WARNING, logger="tip-api"):
        if section == "experience":
            with pytest.raises(EmptyExperienceError):
                await module.build_tailored_cv(profile(), JOB, None)
        else:
            cv = await module.build_tailored_cv(profile(), JOB, None)
            assert cv.education == [] and "no education" in caplog.text
    assert len(calls) == 2 and "invalid profile index" in caplog.text


@pytest.mark.asyncio
async def test_present_and_null_dates_are_copied_as_is(monkeypatch):
    source = profile()
    source.WorkExperiences[0].StartDate = None
    source.WorkExperiences[0].EndDate = "Present"
    calls = provider(monkeypatch, [output(experience=[experience(start_date="2010", end_date=None)])])
    cv = await module.build_tailored_cv(source, JOB, None)
    assert len(calls) == 1
    assert cv.experience[0].start_date is None and cv.experience[0].end_date == "Present"


@pytest.mark.asyncio
async def test_context_and_provider_failures(monkeypatch):
    source = profile()
    source.CoreCompetences = ["private competency"]
    source.AdditionalInformations = ["private information"]
    calls = provider(monkeypatch, [output()])
    await module.build_tailored_cv(source, JOB, None, "French", "  my style  ")
    context = calls[0][1]
    assert "match_score" not in context and context["output_language"] == "French"
    assert context["style_reference"] == "my style"
    assert "CoreCompetences" not in context["profile"] and "AdditionalInformations" not in context["profile"]

    async def fail(*args, **kwargs):
        raise StructuredProviderError("unavailable")

    monkeypatch.setattr(module, "call_openai_structured", fail)
    with pytest.raises(StructuredProviderError):
        await module.build_tailored_cv(source, JOB, None)
