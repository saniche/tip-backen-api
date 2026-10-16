from datetime import date, timedelta

from shared.models import Job


def _auth_headers(user):
    return {"Authorization": f"Bearer {user['access_token']}"}


def _job(
    job_id,
    *,
    posting_date=None,
    status="completed",
    title="Software Engineer",
    company="Example Co",
    location="Remote",
):
    return Job(
        id=job_id,
        url=f"https://jobs.test/{job_id}",
        title=title,
        company=company,
        location=location,
        posting_date=posting_date,
        source="Example Board",
        status=status,
    )


def test_normalized_jobs_requires_authentication(client):
    response = client.get("/api/v1/jobs/normalized")

    assert response.status_code == 401


def test_normalized_jobs_returns_completed_headers_in_default_page(client, user, database_session):
    today = date(2026, 10, 13)
    jobs = [
        _job(f"completed-{index}", posting_date=(today - timedelta(days=index)).isoformat())
        for index in range(22)
    ]
    jobs.extend(
        [
            _job("pending-job", posting_date="2026-10-13", status="pending"),
            _job("failed-job", posting_date="2026-10-13", status="failed"),
        ]
    )
    database_session.add_all(jobs)
    database_session.commit()

    response = client.get("/api/v1/jobs/normalized", headers=_auth_headers(user))

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 22
    assert payload["page"] == 1
    assert payload["limit"] == 20
    assert len(payload["items"]) == 20
    assert [item["postingDate"] for item in payload["items"]] == sorted(
        (today - timedelta(days=index)).isoformat() for index in range(20)
    )[::-1]
    assert all(
        set(item) == {"id", "title", "company", "location", "postingDate", "source"}
        for item in payload["items"]
    )
    assert "pending-job" not in {item["id"] for item in payload["items"]}
    assert "failed-job" not in {item["id"] for item in payload["items"]}


def test_normalized_jobs_puts_missing_and_invalid_dates_last(client, user, database_session):
    database_session.add_all(
        [
            _job("missing-date"),
            _job("invalid-date", posting_date="not-a-date"),
            _job("valid-date", posting_date="2026-10-12"),
            _job("earlier-instant", posting_date="2026-10-12T09:00:00Z"),
            _job("later-instant", posting_date="2026-10-12T12:00:00+02:00"),
        ]
    )
    database_session.commit()

    response = client.get("/api/v1/jobs/normalized", headers=_auth_headers(user))

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["id"] for item in items] == [
        "later-instant",
        "earlier-instant",
        "valid-date",
        "invalid-date",
        "missing-date",
    ]
    assert [item["postingDate"] for item in items] == [
        "2026-10-12T12:00:00+02:00",
        "2026-10-12T09:00:00Z",
        "2026-10-12",
        "not-a-date",
        None,
    ]


def test_normalized_jobs_returns_empty_page_when_no_jobs_exist(client, user):
    response = client.get("/api/v1/jobs/normalized", headers=_auth_headers(user))

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "page": 1, "limit": 20}


def test_normalized_jobs_filters_by_title_company_and_location(client, user, database_session):
    database_session.add_all(
        [
            _job(
                "north-york",
                title="Senior Software Engineer",
                company="North Star Labs",
                location="New York",
            ),
            _job(
                "north-remote",
                title="Product Engineer",
                company="North Star Labs",
                location="Remote",
            ),
            _job(
                "other-remote",
                title="Senior Engineer",
                company="Example Co",
                location="Remote",
            ),
        ]
    )
    database_session.commit()
    headers = _auth_headers(user)

    title_response = client.get("/api/v1/jobs/normalized?title=SOFTWARE", headers=headers)
    company_response = client.get("/api/v1/jobs/normalized?company=north", headers=headers)
    location_response = client.get("/api/v1/jobs/normalized?location=REMOTE", headers=headers)
    combined_response = client.get(
        "/api/v1/jobs/normalized?title=engineer&company=NORTH&location=york",
        headers=headers,
    )
    no_match_response = client.get("/api/v1/jobs/normalized?company=missing", headers=headers)
    blank_filter_response = client.get("/api/v1/jobs/normalized?title=%20%20", headers=headers)

    assert title_response.status_code == 200
    assert {item["id"] for item in title_response.json()["items"]} == {"north-york"}
    assert {item["id"] for item in company_response.json()["items"]} == {"north-york", "north-remote"}
    assert {item["id"] for item in location_response.json()["items"]} == {"north-remote", "other-remote"}
    assert [item["id"] for item in combined_response.json()["items"]] == ["north-york"]
    assert no_match_response.json()["items"] == []
    assert no_match_response.json()["total"] == 0
    assert blank_filter_response.json()["total"] == 3


def test_normalized_jobs_pages_through_stable_date_order(client, user, database_session):
    database_session.add_all(
        [
            _job("latest", posting_date="2026-10-13"),
            _job("tie-b", posting_date="2026-10-12"),
            _job("tie-a", posting_date="2026-10-12"),
            _job("oldest", posting_date="2026-10-11"),
        ]
    )
    database_session.commit()
    headers = _auth_headers(user)

    first_page = client.get("/api/v1/jobs/normalized?page=1&limit=2", headers=headers).json()
    second_page = client.get("/api/v1/jobs/normalized?page=2&limit=2", headers=headers).json()
    beyond_last_page = client.get("/api/v1/jobs/normalized?page=3&limit=2", headers=headers).json()

    assert first_page == {
        "items": [
            {
                "id": "latest",
                "title": "Software Engineer",
                "company": "Example Co",
                "location": "Remote",
                "postingDate": "2026-10-13",
                "source": "Example Board",
            },
            {
                "id": "tie-a",
                "title": "Software Engineer",
                "company": "Example Co",
                "location": "Remote",
                "postingDate": "2026-10-12",
                "source": "Example Board",
            },
        ],
        "total": 4,
        "page": 1,
        "limit": 2,
    }
    assert [item["id"] for item in second_page["items"]] == ["tie-b", "oldest"]
    assert second_page["total"] == first_page["total"] == 4
    assert second_page["page"] == 2
    assert second_page["limit"] == 2
    assert beyond_last_page == {"items": [], "total": 4, "page": 3, "limit": 2}


def test_normalized_jobs_rejects_invalid_pagination_values(client, user):
    headers = _auth_headers(user)

    for params in ({"page": 0}, {"limit": 0}, {"limit": 101}):
        response = client.get("/api/v1/jobs/normalized", params=params, headers=headers)
        assert response.status_code == 422
