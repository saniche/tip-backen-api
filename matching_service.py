from dataclasses import asdict, dataclass, field

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from models import Job, JobMatchingResult, MatchReport, UserProfile
from pipeline.job_matching import build_match_result
from pipeline.llm_matching import JobData, get_llm_match_output


@dataclass
class MatchReportResult:
    id: str
    job_id: str
    score: int
    eligible: bool
    breakdown: dict | None = None
    rank: int | None = None
    explanation: dict | None = None


@dataclass
class MatchReportView:
    id: str
    user_id: str
    profile_id: str
    results: list[MatchReportResult] = field(default_factory=list)


def _job_data(job: Job) -> JobData:
    return JobData(
        title=job.title,
        required=job.required,
        desirable=job.desirable,
        technical_stack=job.technical_stack,
        key_responsibilities=job.key_responsibilities,
        company=job.company,
        location=job.location,
        salary=job.salary,
        url=job.url,
        source=job.source,
        summary=job.summary,
    )


def _view(report: MatchReport, results: list[JobMatchingResult]) -> MatchReportView:
    return MatchReportView(
        id=report.id,
        user_id=report.user_id,
        profile_id=report.profile_id,
        results=[
            MatchReportResult(
                id=result.id,
                job_id=result.job_id,
                score=int(result.score),
                eligible=result.eligible,
                breakdown=result.breakdown,
                rank=result.rank,
                explanation=result.llm_match_output,
            )
            for result in sorted(results, key=lambda item: (item.rank or 0, -item.score))
        ],
    )


def create_match_report(db: Session, user_id: str, job_ids: list[str]) -> MatchReportView:
    if not job_ids:
        raise ValueError("At least one job id is required")
    profile = db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id).order_by(desc(UserProfile.created_at))
    ).scalars().first()
    if profile is None:
        raise ValueError("Profile not found")
    jobs = {job.id: job for job in db.execute(select(Job).where(Job.id.in_(job_ids))).scalars().all()}
    if any(job_id not in jobs for job_id in job_ids):
        raise ValueError("Job not found")

    report = MatchReport(user_id=user_id, profile_id=profile.id, rules_version="v1")
    db.add(report)
    db.flush()
    persisted = []
    for job_id in job_ids:
        job = jobs[job_id]
        llm_output = get_llm_match_output(profile.data, _job_data(job))
        scored = build_match_result(llm_output)
        result = JobMatchingResult(
            report_id=report.id,
            user_id=user_id,
            job_id=job.id,
            profile_id=profile.id,
            score=scored.score,
            eligible=scored.eligible,
            scoring_status=scored.scoring_status,
            breakdown={"groups": scored.breakdown, "effective_weights": scored.effective_weights},
            llm_match_output=asdict(llm_output),
            profile_snapshot=dict(profile.data),
            job_snapshot={"id": job.id, "title": job.title, "company": job.company, "location": job.location, "required": job.required, "desirable": job.desirable, "technical_stack": job.technical_stack},
            rules_version="v1",
        )
        db.add(result)
        persisted.append(result)
    for rank, result in enumerate(sorted(persisted, key=lambda item: item.score, reverse=True), start=1):
        result.rank = rank
    db.commit()
    return _view(report, persisted)


def list_match_reports(db: Session, user_id: str) -> list[MatchReportView]:
    reports = db.execute(select(MatchReport).where(MatchReport.user_id == user_id).order_by(desc(MatchReport.created_at))).scalars().all()
    return [_view(report, db.execute(select(JobMatchingResult).where(JobMatchingResult.report_id == report.id)).scalars().all()) for report in reports]


def get_match_report(db: Session, user_id: str, report_id: str) -> MatchReportView:
    report = db.get(MatchReport, report_id)
    if report is None or report.user_id != user_id:
        raise PermissionError("Forbidden")
    results = db.execute(select(JobMatchingResult).where(JobMatchingResult.report_id == report.id)).scalars().all()
    return _view(report, results)
