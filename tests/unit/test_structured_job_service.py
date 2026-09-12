import pytest

import job_service


@pytest.mark.asyncio
async def test_normalize_job_content_returns_validated_canonical_shape(monkeypatch):
    async def fake_call(*args, **kwargs):
        schema = args[2]
        return schema(
            key_responsibilities=["Build APIs"], required={"qualifications": [], "skills": ["Python"]},
            desirable={"qualifications": [], "skills": []}, technical_stack=["Python"],
        )

    monkeypatch.setattr(job_service, "call_openai_structured", fake_call)
    job = await job_service.normalize_job_content("Build APIs with Python")

    assert job["required"]["skills"] == ["Python"]
    assert job["desirable"]["qualifications"] == []