import pytest

from llm_structured import StructuredProviderError
from matching_service import create_match_report, get_match_report, list_match_reports
from models import Job, JobMatchingResult, MatchReport, User, UserProfile


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

    monkeypatch.setattr("matching_service.get_llm_match_output", fail_matching)
    with pytest.raises(StructuredProviderError):
        await create_match_report(database_session, user.id, [job.id])

    assert database_session.query(MatchReport).count() == 0
    assert database_session.query(JobMatchingResult).count() == 0
