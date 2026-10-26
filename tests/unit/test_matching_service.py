import pytest

from matching.matching_service import _job_data, create_match_report, get_match_report, list_match_reports
from shared.llm_structured import StructuredProviderError
from shared.models import Job, JobMatchingResult, MatchReport, User, UserProfile


def test_job_data_maps_flat_normalized_requirements_for_matching():
    job = Job(
        title="Python Engineer",
        required=["Python", "FastAPI"],
        desirable=["Kubernetes"],
        technical_stack=["Python"],
    )

    job_data = _job_data(job)

    assert job_data.required == {"qualifications": [], "skills": ["Python", "FastAPI"]}
    assert job_data.desirable == {"qualifications": [], "skills": ["Kubernetes"]}


@pytest.mark.asyncio
async def test_match_report_creation_and_ownership(database_session):
    user = User(email="match@example.com", hashed_password="hash")
    database_session.add(user)
    database_session.commit()
    database_session.refresh(user)

    profile = UserProfile(
        user_id=user.id, data={"summary": "Python engineer", "skills": ["Python", "FastAPI"]}, output_language="English"
    )
    database_session.add(profile)
    database_session.commit()

    job = Job(
        title="Python Engineer",
        company="Acme",
        location="Remote",
        summary="Build APIs in Python",
        url="https://jobs.example/py",
        required={"qualifications": ["Bachelor's degree"], "skills": ["Python"]},
        desirable={"qualifications": [], "skills": ["FastAPI"]},
        technical_stack=["Python", "FastAPI"],
        submitter_id=user.id,
    )
    database_session.add(job)
    database_session.commit()
    database_session.refresh(job)

    report = await create_match_report(database_session, user.id, [job.id])

    assert report is not None
    assert len(report.results) == 1
    assert report.results[0].job_id == job.id
    assert report.results[0].score >= 0
    assert len(list_match_reports(database_session, user.id)) == 1
    assert get_match_report(database_session, user.id, report.id).id == report.id
    persisted = database_session.query(JobMatchingResult).one()
    assert persisted.profile_id == report.profile_id
    assert persisted.rules_version == "v2"
    assert set(persisted.llm_match_output) == {"requirements", "desirables", "notes", "analysis"}

    other_user = User(email="other@example.com", hashed_password="hash")
    database_session.add(other_user)
    database_session.commit()
    with pytest.raises(PermissionError):
        get_match_report(database_session, other_user.id, report.id)


@pytest.mark.asyncio
async def test_match_report_rejects_missing_profile_and_unavailable_job(database_session):
    user = User(email="missing-profile@example.com", hashed_password="hash")
    database_session.add(user)
    database_session.commit()
    with pytest.raises(ValueError, match="Profile not found"):
        await create_match_report(database_session, user.id, ["missing-job"])


@pytest.mark.asyncio
async def test_match_report_keeps_profile_and_job_snapshots(database_session):
    user = User(email="snapshot@example.com", hashed_password="hash")
    database_session.add(user)
    database_session.commit()
    profile = UserProfile(user_id=user.id, data={"skills": ["Python"]}, output_language="English")
    job = Job(
        title="Python Engineer",
        url="https://jobs.example/snapshot",
        required={"qualifications": [], "skills": ["Python"]},
        desirable={"qualifications": [], "skills": []},
        technical_stack=["Python"],
        submitter_id=user.id,
    )
    database_session.add_all([profile, job])
    database_session.commit()
    database_session.refresh(job)

    report = await create_match_report(database_session, user.id, [job.id])
    result = database_session.query(JobMatchingResult).first()

    assert report.results[0].score >= 0
    assert result.profile_snapshot["skills"] == ["Python"]
    assert result.job_snapshot["title"] == "Python Engineer"
    assert result.rank == 1
    assert job.required == {"qualifications": [], "skills": ["Python"]}
    assert job.desirable == {"qualifications": [], "skills": []}
    assert job.technical_stack == ["Python"]
    assert job.key_responsibilities == []


@pytest.mark.asyncio
async def test_empty_criteria_persist_null_score(database_session):
    user = User(email="empty-criteria@example.com", hashed_password="hash")
    database_session.add(user)
    database_session.commit()
    profile = UserProfile(user_id=user.id, data={"skills": ["Python"]}, output_language="English")
    job = Job(
        title="No criteria",
        required=[],
        desirable=[],
        technical_stack=["Python"],
        key_responsibilities=["Build APIs"],
        submitter_id=user.id,
    )
    database_session.add_all([profile, job])
    database_session.commit()
    database_session.refresh(job)

    report = await create_match_report(database_session, user.id, [job.id])
    persisted = database_session.query(JobMatchingResult).one()

    assert report.results[0].score is None
    assert persisted.score is None
    assert persisted.scoring_status == "unscorable"
    assert persisted.eligible is False
    assert persisted.profile_id == profile.id
    assert persisted.llm_match_output["requirements"] == []
    assert persisted.llm_match_output["desirables"] == []


@pytest.mark.asyncio
async def test_match_provider_failure_does_not_persist_partial_report(database_session, monkeypatch):
    user = User(email="provider-failure@example.com", hashed_password="hash")
    database_session.add(user)
    database_session.commit()
    profile = UserProfile(user_id=user.id, data={"skills": ["Python"]}, output_language="English")
    job = Job(
        title="Python Engineer", url="https://jobs.example/provider-failure",
        required={"qualifications": [], "skills": ["Python"]}, desirable={"qualifications": [], "skills": []},
        technical_stack=["Python"], submitter_id=user.id,
    )
    database_session.add_all([profile, job])
    database_session.commit()

    async def fail_matching(*args, **kwargs):
        raise StructuredProviderError("External processing failed.")

    monkeypatch.setattr("matching.matching_service.get_llm_match_output", fail_matching)
    with pytest.raises(StructuredProviderError):
        await create_match_report(database_session, user.id, [job.id])

    assert database_session.query(MatchReport).count() == 0
    assert database_session.query(JobMatchingResult).count() == 0


def test_legacy_matching_output_remains_readable(database_session):
    user = User(email="legacy-match@example.com", hashed_password="hash")
    database_session.add(user)
    database_session.commit()
    profile = UserProfile(user_id=user.id, data={"skills": ["Python"]}, output_language="English")
    job = Job(title="Legacy", required=[], desirable=[], submitter_id=user.id)
    database_session.add_all([profile, job])
    database_session.commit()
    report = MatchReport(user_id=user.id, profile_id=profile.id, status="completed", rules_version="v1")
    database_session.add(report)
    database_session.flush()
    result = JobMatchingResult(
        report_id=report.id,
        user_id=user.id,
        job_id=job.id,
        profile_id=profile.id,
        score=82,
        eligible=True,
        scoring_status="scored",
        llm_match_output={
            "required_skills": [{"result": "Partial", "value": "Python", "rationale": "Legacy evidence."}]
        },
        rules_version="v1",
        rank=1,
    )
    database_session.add(result)
    database_session.commit()

    legacy_view = get_match_report(database_session, user.id, report.id)

    assert legacy_view.results[0].score == 82
    assert legacy_view.results[0].explanation["required_skills"][0]["result"] == "Partial"
