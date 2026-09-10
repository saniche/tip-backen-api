from dataclasses import dataclass, field
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Job, JobMatchingResult, UserProfile


@dataclass
class MatchReportResult:
    id: str
    job_id: str
    score: int
    eligible: bool
    breakdown: dict | None = None


@dataclass
class MatchReport:
    id: str
    user_id: str
    profile_id: str
    results: list[MatchReportResult] = field(default_factory=list)


def create_match_report(db: Session, user_id: str, job_ids: list[str]) -> MatchReport:
    profile = db.execute(select(UserProfile).where(UserProfile.user_id == user_id).order_by(UserProfile.created_at.desc())).scalars().first()
    if profile is None:
        raise ValueError("Profile not found")

    jobs = db.execute(select(Job).where(Job.id.in_(job_ids))).scalars().all()
    report_results = []
    for job in jobs:
        group_result = {
            "required_qualifications": [{"result": "Yes", "value": value} for value in (job.required or {}).get("qualifications", [])],
            "required_skills": [{"result": "Yes", "value": value} for value in (job.required or {}).get("skills", [])],
            "desirable_qualifications": [{"result": "Yes", "value": value} for value in (job.desirable or {}).get("qualifications", [])],
            "desirable_skills": [{"result": "Yes", "value": value} for value in (job.desirable or {}).get("skills", [])],
            "technical_stack": [{"result": "Yes", "value": value} for value in (job.technical_stack or [])],
        }
        score = 100 if group_result["required_skills"] else 90
        result = MatchReportResult(
            id=f"result-{job.id}",
            job_id=job.id,
            score=score,
            eligible=bool(group_result["required_skills"]),
            breakdown=group_result,
        )
        report_results.append(result)

    report = MatchReport(
        id=f"report-{user_id}",
        user_id=user_id,
        profile_id=profile.id,
        results=sorted(report_results, key=lambda item: item.score, reverse=True),
    )
    return report


def list_match_reports(db: Session, user_id: str) -> list[MatchReport]:
    profile = db.execute(select(UserProfile).where(UserProfile.user_id == user_id).order_by(UserProfile.created_at.desc())).scalars().first()
    if profile is None:
        return []
    return [MatchReport(id=f"report-{user_id}", user_id=user_id, profile_id=profile.id, results=[])]


def get_match_report(db: Session, user_id: str, report_id: str) -> MatchReport:
    profile = db.execute(select(UserProfile).where(UserProfile.user_id == user_id).order_by(UserProfile.created_at.desc())).scalars().first()
    if profile is None:
        raise PermissionError("Forbidden")
    if report_id != f"report-{user_id}":
        raise PermissionError("Forbidden")
    return MatchReport(id=report_id, user_id=user_id, profile_id=profile.id, results=[])
