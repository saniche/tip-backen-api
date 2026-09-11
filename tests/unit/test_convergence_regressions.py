from datetime import datetime, timedelta, timezone

from models import Job
from pipeline.job_matching import build_match_result
from pipeline.llm_matching import LlmMatchOutput
from profile_service import consolidate_profile_fragments


def test_profile_consolidation_preserves_user_edit_over_later_extraction():
    merged = consolidate_profile_fragments(
        [
            {"data": {"summary": "original"}, "evidence_type": "extracted"},
            {"data": {"summary": "confirmed"}, "evidence_type": "user_edited"},
            {"data": {"summary": "later extraction"}, "evidence_type": "extracted"},
        ]
    )

    assert merged["summary"] == "confirmed"


def test_match_result_classifies_no_requirements_as_ineligible():
    result = build_match_result(
        LlmMatchOutput(required_skills=[{"result": "No", "value": "Python", "rationale": "missing"}])
    )

    assert result.score == 0
    assert result.eligible is False
    assert result.breakdown["required_skills"] == 0.0


def test_job_created_at_can_be_filtered_by_saved_date(database_session):
    older = Job(url="https://jobs.test/old", title="Old", created_at=datetime.now(timezone.utc) - timedelta(days=2))
    newer = Job(url="https://jobs.test/new", title="New", created_at=datetime.now(timezone.utc))
    database_session.add_all([older, newer])
    database_session.commit()

    jobs = database_session.query(Job).order_by(Job.created_at.desc()).all()

    assert [job.title for job in jobs] == ["New", "Old"]
