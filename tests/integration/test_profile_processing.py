import time

import profile_builder_router
from llm_structured import StructuredProviderError
from pipeline.profile_builder import CertificateEntry, Education, SkillEntry, UserProfile, WorkExperience


def test_profile_processing_completes_and_preserves_edit(client):
    token = client.post(
        "/api/v1/auth/register", json={"email": "profile-int@example.com", "password": "password123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    session = client.post("/api/v1/profile/sessions", headers=headers).json()

    upload = client.post(
        f"/api/v1/profile/sessions/{session['id']}/files",
        headers=headers,
        files={"file": ("resume.txt", b"Python engineer", "text/plain")},
    )
    assert upload.status_code == 202
    for _ in range(20):
        profile = client.get("/api/v1/profile", headers=headers)
        if profile.status_code == 200:
            break
        time.sleep(0.01)
    assert profile.status_code == 200

    updated = client.put("/api/v1/profile", headers=headers, json={"data": {"summary": "user confirmed"}})
    assert updated.status_code == 200
    assert updated.json()["data"]["summary"] == "user confirmed"


def test_profile_processing_persists_complete_structured_profile(client, monkeypatch):
    token = client.post(
        "/api/v1/auth/register", json={"email": "profile-complete@example.com", "password": "password123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    session = client.post("/api/v1/profile/sessions", headers=headers).json()

    async def complete_profile(*args, **kwargs):
        return UserProfile(
            Name="Ada Lovelace",
            Email="ada@example.com",
            Phone="+1 555 0100",
            Location="London",
            LinkedIn="https://linkedin.example/ada",
            Summary="Python engineer",
            SoftSkills=["Communication"],
            Languages=["English"],
            Certifications=[CertificateEntry(Name="Cloud Architect", Issuer="Cloud Org", Year="2024")],
            WorkExperiences=[WorkExperience(Company="Analytical Engines", Title="Engineer", Summary="Built systems")],
            Education=[Education(Institution="University", Degree="BSc", Field="Mathematics", Year="1843")],
            TotalYearsOfExperience=5,
            PreferredJobTitles=["Staff Engineer"],
            PreferredLocations=["Remote"],
            TechnicalSkills=[SkillEntry(Name="Python", Level="high")],
        )

    monkeypatch.setattr(profile_builder_router, "extract_profile", complete_profile)
    upload = client.post(
        f"/api/v1/profile/sessions/{session['id']}/files",
        headers=headers,
        files={"file": ("resume.txt", b"complete resume", "text/plain")},
    )

    assert upload.status_code == 202
    profile = client.get("/api/v1/profile", headers=headers)
    data = profile.json()["data"]
    assert data["email"] == "ada@example.com"
    assert data["certifications"] == [{"Name": "Cloud Architect", "Issuer": "Cloud Org", "Year": "2024"}]
    assert data["work_experiences"] == [
        {"Company": "Analytical Engines", "Title": "Engineer", "StartDate": None, "EndDate": None, "Summary": "Built systems"}
    ]
    assert data["education"] == [
        {"Institution": "University", "Degree": "BSc", "Field": "Mathematics", "Year": "1843"}
    ]
    assert data["total_years_of_experience"] == 5
    assert data["preferred_job_titles"] == ["Staff Engineer"]
    assert data["skills"] == [{"Name": "Python", "Level": "high"}]


def test_profile_provider_failure_marks_file_and_job_failed(client, monkeypatch):
    token = client.post(
        "/api/v1/auth/register", json={"email": "profile-failure@example.com", "password": "password123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    session = client.post("/api/v1/profile/sessions", headers=headers).json()

    async def fail_profile(*args, **kwargs):
        raise StructuredProviderError("provider unavailable")

    monkeypatch.setattr(profile_builder_router, "extract_profile", fail_profile)
    upload = client.post(
        f"/api/v1/profile/sessions/{session['id']}/files", headers=headers,
        files={"file": ("resume.txt", b"Python engineer", "text/plain")},
    ).json()
    status = client.get(f"/api/v1/processing-jobs/{upload['processing_job_id']}", headers=headers).json()
    detail = client.get(f"/api/v1/profile/sessions/{session['id']}", headers=headers).json()

    assert status["status"] == "failed"
    assert detail["status"] == "failed"
    assert detail["files"][0]["status"] == "failed"


def test_profile_invalid_structured_output_marks_processing_failed(client, monkeypatch):
    token = client.post(
        "/api/v1/auth/register", json={"email": "profile-invalid@example.com", "password": "password123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    session = client.post("/api/v1/profile/sessions", headers=headers).json()

    async def invalid_profile(*args, **kwargs):
        raise StructuredProviderError("invalid structured output")

    monkeypatch.setattr(profile_builder_router, "extract_profile", invalid_profile)
    upload = client.post(
        f"/api/v1/profile/sessions/{session['id']}/files", headers=headers,
        files={"file": ("resume.txt", b"Python engineer", "text/plain")},
    ).json()

    assert client.get(f"/api/v1/processing-jobs/{upload['processing_job_id']}", headers=headers).json()["status"] == "failed"
    assert client.get("/api/v1/profile", headers=headers).status_code == 404
