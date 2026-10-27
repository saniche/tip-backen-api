from datetime import date, timedelta

import pytest
from pydantic import ValidationError

import jobs.job_service as job_service


@pytest.mark.asyncio
async def test_normalize_job_content_returns_validated_canonical_shape(monkeypatch):
    async def fake_call(system, user, schema, **kwargs):
        assert "https://www.indeed.com/viewjob?jk=123" in user
        assert "Processing date (UTC):" in user
        assert "Build APIs with Python" in user
        assert "no explanations, commentary" in system
        assert kwargs["operation"] == "job_normalizer"
        return schema(
            title="Software Engineer",
            company="Example Inc.",
            location="Remote",
            salary="",
            source="Indeed",
            posting_date="2026-10-15",
            key_responsibilities=["Build APIs"],
            requirements=["Python"],
            desirables=[],
            tools_and_technologies=["Python"],
            additionals=[],
        )

    monkeypatch.setattr(job_service, "call_openai_structured", fake_call)
    job = await job_service.normalize_job_content(
        "https://www.indeed.com/viewjob?jk=123", "Build APIs with Python"
    )

    assert job["title"] == "Software Engineer"
    assert job["company"] == "Example Inc."
    assert job["source"] == "Indeed"
    assert job["requirements"] == ["Python"]
    assert job["desirables"] == []
    assert job["tools_and_technologies"] == ["Python"]
    assert "technical_stack" not in job
    assert job["additionals"] == []
    assert set(job) == {
        "title",
        "company",
        "location",
        "salary",
        "source",
        "posting_date",
        "key_responsibilities",
        "requirements",
        "desirables",
        "tools_and_technologies",
        "additionals",
    }
    with pytest.raises(ValidationError):
        job_service.JobNormalizationOutput(
            title="Engineer",
            company="Example",
            location="",
            salary="",
            source="Other",
            posting_date=None,
            key_responsibilities=[],
            requirements=[],
            desirables=[],
            tools_and_technologies=[],
            additionals=[],
            explanation="not allowed",
        )
    with pytest.raises(ValidationError):
        job_service.JobNormalizationOutput(
            title="Engineer",
            company="Example",
            location="",
            salary="",
            source="Other",
            posting_date=None,
            key_responsibilities=[],
            requirements=[],
            desirables=[],
            technical_stack=[],
            additionals=[],
        )


@pytest.mark.asyncio
async def test_normalize_job_content_defaults_missing_date_to_yesterday(monkeypatch):
    reference_dates = []

    async def fake_call(system, user, schema, **kwargs):
        reference_date = user.split("Processing date (UTC): ", maxsplit=1)[1].splitlines()[0]
        reference_dates.append(date.fromisoformat(reference_date))
        return schema(
            title="Software Engineer",
            company="",
            location="",
            salary="",
            source="Other",
            posting_date=None,
            key_responsibilities=[],
            requirements=[],
            desirables=[],
            tools_and_technologies=[],
            additionals=[],
        )

    monkeypatch.setattr(job_service, "call_openai_structured", fake_call)
    job = await job_service.normalize_job_content("https://jobs.example/1", "Software Engineer")

    assert job["posting_date"] == (reference_dates[0] - timedelta(days=1)).isoformat()