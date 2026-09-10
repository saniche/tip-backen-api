from dataclasses import dataclass, field
from typing import Any


@dataclass
class CertificateEntry:
    Name: str
    Issuer: str | None = None
    Year: str | None = None


@dataclass
class Education:
    Institution: str | None = None
    Degree: str | None = None
    Field: str | None = None
    Year: str | None = None


@dataclass
class SkillEntry:
    Name: str
    Level: str = "medium"


@dataclass
class WorkExperience:
    Company: str | None = None
    Title: str | None = None
    StartDate: str | None = None
    EndDate: str | None = None
    Summary: str | None = None


@dataclass
class UserProfile:
    Name: str = ""
    Email: str = ""
    Phone: str = ""
    Location: str = ""
    LinkedIn: str = ""
    Summary: str = ""
    SoftSkills: list[str] = field(default_factory=list)
    Languages: list[str] = field(default_factory=list)
    Certifications: list[CertificateEntry] = field(default_factory=list)
    WorkExperiences: list[WorkExperience] = field(default_factory=list)
    Education: list[Education] = field(default_factory=list)
    TotalYearsOfExperience: int = 0
    PreferredJobTitles: list[str] = field(default_factory=list)
    PreferredLocations: list[str] = field(default_factory=list)
    TechnicalSkills: list[SkillEntry] = field(default_factory=list)


def extract_profile(document: Any) -> UserProfile:
    payload = document if isinstance(document, dict) else {"content": str(document)}
    text = str(payload.get("content") or payload.get("text") or "")
    summary = text.strip()[:400] if text else "Profile extracted from document."
    skills = [item.strip() for item in payload.get("skills", []) if item and str(item).strip()]
    if not skills:
        tokens = [part for part in summary.replace("\n", " ").split() if len(part) > 4]
        skills = tokens[:5]
    return UserProfile(
        Name=payload.get("name") or "",
        Email=payload.get("email") or "",
        Phone=payload.get("phone") or "",
        Location=payload.get("location") or "",
        LinkedIn=payload.get("linkedin") or "",
        Summary=summary,
        SoftSkills=[str(x) for x in payload.get("soft_skills", [])],
        Languages=[str(x) for x in payload.get("languages", [])],
        Certifications=[CertificateEntry(Name=str(x)) for x in payload.get("certifications", [])],
        WorkExperiences=[
            WorkExperience(
                Company=str(item.get("company") or ""),
                Title=str(item.get("title") or ""),
                StartDate=str(item.get("start_date") or ""),
                EndDate=str(item.get("end_date") or ""),
                Summary=str(item.get("summary") or ""),
            )
            for item in payload.get("work_experiences", [])
            if isinstance(item, dict)
        ],
        Education=[
            Education(
                Institution=str(item.get("institution") or ""),
                Degree=str(item.get("degree") or ""),
                Field=str(item.get("field") or ""),
                Year=str(item.get("year") or ""),
            )
            for item in payload.get("education", [])
            if isinstance(item, dict)
        ],
        TotalYearsOfExperience=int(payload.get("total_years_of_experience") or 0),
        PreferredJobTitles=[str(x) for x in payload.get("preferred_job_titles", [])],
        PreferredLocations=[str(x) for x in payload.get("preferred_locations", [])],
        TechnicalSkills=[SkillEntry(Name=str(s)) for s in skills],
    )
