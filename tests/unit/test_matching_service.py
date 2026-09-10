import pytest

from matching_service import create_match_report, get_match_report, list_match_reports
from models import Job, User, UserProfile


def test_match_report_creation_and_ownership(database_session):
    user = User(email="match@example.com", hashed_password="hash")
    database_session.add(user)
    database_session.commit()
    database_session.refresh(user)

    profile = UserProfile(user_id=user.id, data={"summary": "Python engineer", "skills": ["Python", "FastAPI"]}, output_language="English")
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

    report = create_match_report(database_session, user.id, [job.id])

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
