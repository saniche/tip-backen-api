import os
import ast

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("AZURE_STORAGE_CONNECTION_STRING", "UseDevelopmentStorage=true")

import pytest
from fastapi.testclient import TestClient

import cv.cv_tailoring_router as cv_tailoring_router
import jobs.job_normalizer as job_normalizer
import jobs.job_service as job_service
import matching.matching_service as matching_service
import matching.job_matching_router as job_matching_router
import cv.cv_tailoring as cv_tailoring
import matching.llm_matching as llm_matching
import profile.profile_builder as profile_builder
import profile.profile_builder_router as profile_builder_router
from shared.database import Base, TestingSessionLocal, get_db, get_testing_db, testing_engine
from main import app


@pytest.fixture(autouse=True)
def database():
    profile_builder_router.SessionLocal = TestingSessionLocal
    cv_tailoring_router.SessionLocal = TestingSessionLocal
    job_normalizer.SessionLocal = TestingSessionLocal
    job_matching_router.SessionLocal = TestingSessionLocal
    Base.metadata.create_all(testing_engine)
    yield
    Base.metadata.drop_all(testing_engine)


@pytest.fixture(autouse=True)
def structured_ai_provider(monkeypatch):
    async def fake_call(system, user, schema_model, *, operation, model=None):
        if operation == "profile_builder":
            return schema_model(
                Name="Test Candidate", Email="", Phone="", Location="", LinkedIn="", Summary="Python engineer",
                SoftSkills=[], Languages=["English"], Certifications=[], WorkExperiences=[], Education=[],
                TotalYearsOfExperience=0, PreferredJobTitles=[], PreferredLocations=[],
                TechnicalSkills=[{"Name": "Python", "Level": "medium"}],
            )
        if operation == "job_normalizer":
            return schema_model(
                key_responsibilities=["Build APIs"],
                required={"qualifications": [], "skills": ["Python"]},
                desirable={"qualifications": [], "skills": ["FastAPI"]},
                technical_stack=["Python", "FastAPI"],
            )
        if operation == "job_matching":
            context = ast.literal_eval(user)
            job = context["job"]
            profile_text = str(context["profile"]).lower()

            def assessments(values):
                return [
                    {
                        "result": "Yes" if str(value).lower() in profile_text else "No",
                        "value": str(value),
                        "rationale": (
                            f"Profile contains {value}."
                            if str(value).lower() in profile_text
                            else f"No profile evidence found for {value}."
                        ),
                    }
                    for value in values
                ]

            return schema_model(
                required_qualifications=assessments(job.get("required", {}).get("qualifications", [])),
                required_skills=assessments(job.get("required", {}).get("skills", [])),
                desirable_qualifications=assessments(job.get("desirable", {}).get("qualifications", [])),
                desirable_skills=assessments(job.get("desirable", {}).get("skills", [])),
                technical_stack=assessments(job.get("technical_stack", [])), notes="Validated profile-to-job comparison.",
            )
        if operation == "cv_tailoring":
            return schema_model(
                target_role="Python Engineer", summary="Python Engineer",
                experience=[], education=[], certifications=[], skills=["Python"], summary_evidence=["Python Engineer"],
                experience_evidence=[], education_evidence=[], certification_evidence=[],
            )
        raise AssertionError(f"Unexpected operation: {operation}")

    monkeypatch.setattr(profile_builder, "call_openai_structured", fake_call)
    monkeypatch.setattr(job_service, "call_openai_structured", fake_call)
    monkeypatch.setattr(llm_matching, "call_openai_structured", fake_call)
    monkeypatch.setattr(cv_tailoring, "call_openai_structured", fake_call)


@pytest.fixture
def database_session(database):
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = get_testing_db
    return TestClient(app)


@pytest.fixture
def user(client):
    response = client.post("/api/v1/auth/register", json={"email": "user@example.com", "password": "password123"})
    return response.json()
