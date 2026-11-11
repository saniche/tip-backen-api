from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shared.models import ApplicationJournal, ApplicationStatus, CVRequest, Job, JobInterest, MatchReport, UserProfile

_FINISHED_STATUSES = (ApplicationStatus.CLOSED, ApplicationStatus.REJECTED, ApplicationStatus.ACCEPTED)


def get_dashboard_summary(db: Session, user_id: str, today: date, follow_up_limit: int) -> dict:
    status_counts = {status.value: 0 for status in ApplicationStatus}
    rows = db.execute(
        select(ApplicationJournal.status, func.count(ApplicationJournal.id))
        .where(ApplicationJournal.user_id == user_id)
        .group_by(ApplicationJournal.status)
    ).all()
    for application_status, count in rows:
        status_counts[application_status.value] = count

    due_conditions = (
        ApplicationJournal.user_id == user_id,
        ApplicationJournal.follow_up_date.is_not(None),
        ApplicationJournal.follow_up_date <= today,
        ApplicationJournal.status.not_in(_FINISHED_STATUSES),
    )
    due_count = db.scalar(select(func.count(ApplicationJournal.id)).where(*due_conditions))
    due_items = db.execute(
        select(ApplicationJournal.id, Job.title, Job.company, ApplicationJournal.follow_up_date)
        .join(Job, Job.id == ApplicationJournal.job_id)
        .where(*due_conditions)
        .order_by(ApplicationJournal.follow_up_date.asc(), ApplicationJournal.id.asc())
        .limit(follow_up_limit)
    ).all()

    return {
        "applications": {
            "total": sum(status_counts.values()),
            "by_status": status_counts,
            "follow_ups_due": {
                "count": due_count,
                "items": [
                    {"id": entry_id, "job_title": title, "company": company, "follow_up_date": follow_up_date}
                    for entry_id, title, company, follow_up_date in due_items
                ],
            },
        },
        "interests": {"total": db.scalar(select(func.count(JobInterest.id)).where(JobInterest.user_id == user_id))},
        "matching_reports": {
            "total": db.scalar(select(func.count(MatchReport.id)).where(MatchReport.user_id == user_id))
        },
        "tailoring_requests": {
            "total": db.scalar(select(func.count(CVRequest.id)).where(CVRequest.user_id == user_id))
        },
        "profiles": {
            "total": db.scalar(
                select(func.count(UserProfile.id)).where(
                    UserProfile.user_id == user_id, UserProfile.deleted_at.is_(None)
                )
            )
        },
    }
