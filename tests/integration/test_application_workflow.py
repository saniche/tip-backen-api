import pytest

from shared.models import ApplicationJournal, ApplicationStatusHistory, Job, JobInterest, User


def _register(client, session, email):
    token = client.post("/api/v1/auth/register", json={"email": email, "password": "password123"}).json()[
        "access_token"
    ]
    return {"Authorization": "Bearer " + token}, session.query(User).filter(User.email == email).one().id


def test_journal_creation_and_interest_release_roll_back_together(client, database_session, monkeypatch):
    import applications.application_service as application_service
    from shared.schemas import ApplicationCreate

    _, user_id = _register(client, database_session, "workflow-atomic@example.com")
    job = Job(url="https://jobs.test/workflow-atomic", title="Engineer", status="completed")
    database_session.add(job)
    database_session.flush()
    database_session.add(JobInterest(user_id=user_id, job_id=job.id))
    database_session.commit()

    release = application_service.release_interest

    def fail_after_release(db, owner_id, job_id):
        release(db, owner_id, job_id)
        raise RuntimeError("simulated failure after interest removal")

    monkeypatch.setattr(application_service, "release_interest", fail_after_release)

    with pytest.raises(RuntimeError, match="simulated failure after interest removal"):
        application_service.create_application(database_session, user_id, ApplicationCreate(jobId=job.id))
    assert database_session.query(ApplicationJournal).filter_by(user_id=user_id, job_id=job.id).count() == 0
    assert database_session.query(ApplicationStatusHistory).count() == 0
    assert database_session.query(JobInterest).filter_by(user_id=user_id, job_id=job.id).count() == 1


def test_status_history_is_chronological_and_job_header_is_current(client, database_session):
    headers, user_id = _register(client, database_session, "workflow-history@example.com")
    job = Job(
        url="https://jobs.test/workflow-history",
        title="Original title",
        company="Original company",
        location="Remote",
        status="completed",
    )
    database_session.add(job)
    database_session.commit()

    created = client.post("/api/v1/applications", headers=headers, json={"jobId": job.id})
    application_id = created.json()["id"]
    database_session.refresh(job)
    job.title = "Updated title"
    job.company = "Updated company"
    database_session.commit()
    client.patch(
        f"/api/v1/applications/{application_id}/status",
        headers=headers,
        json={"status": "Applied", "note": "Submitted"},
    )
    response = client.patch(
        f"/api/v1/applications/{application_id}/status",
        headers=headers,
        json={"status": "Interview", "note": "Interview scheduled"},
    )

    item = response.json()
    assert item["job"]["title"] == "Updated title"
    assert item["job"]["company"] == "Updated company"
    assert [event["status"] for event in item["history"]] == ["NotStarted", "Applied", "Interview"]
    assert [event["date"] for event in item["history"]] == sorted(event["date"] for event in item["history"])
    assert item["status"] == item["history"][-1]["status"]
    assert database_session.query(ApplicationJournal).filter_by(id=application_id, user_id=user_id).count() == 1
