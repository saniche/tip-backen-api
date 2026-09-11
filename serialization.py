"""
Conversion helpers between the pipeline modules' dataclasses and plain dicts, for storing/loading
from the DB's JSON columns. dataclasses.asdict() handles the dataclass -> dict direction; the
reverse needs explicit reconstruction since asdict() flattens nested dataclasses into nested dicts.
"""

from dataclasses import asdict

from pipeline.profile_builder import CertificateEntry, Education, SkillEntry, UserProfile, WorkExperience


def user_profile_to_dict(profile: UserProfile) -> dict:
    return asdict(profile)


def dict_to_user_profile(d: dict) -> UserProfile:
    if not isinstance(d, dict):
        return UserProfile()

    raw_skills = d.get("TechnicalSkills", d.get("skills", []))
    if isinstance(raw_skills, list):
        technical_skills = [SkillEntry(**s) if isinstance(s, dict) else SkillEntry(Name=str(s)) for s in raw_skills]
    else:
        technical_skills = [SkillEntry(Name=str(raw_skills))] if raw_skills else []

    def as_list(key: str, fallback: list | None = None) -> list:
        value = d.get(key, fallback or [])
        return value if isinstance(value, list) else [value] if value else []

    return UserProfile(
        Name=str(d.get("Name") or d.get("name") or ""),
        Email=str(d.get("Email") or d.get("email") or ""),
        Phone=str(d.get("Phone") or d.get("phone") or ""),
        Location=str(d.get("Location") or d.get("location") or ""),
        LinkedIn=str(d.get("LinkedIn") or d.get("linkedin") or ""),
        Summary=str(d.get("Summary") or d.get("summary") or ""),
        SoftSkills=[str(item) for item in as_list("SoftSkills", d.get("soft_skills", []))],
        Languages=[str(item) for item in as_list("Languages", d.get("languages", []))],
        Certifications=[
            CertificateEntry(**c) if isinstance(c, dict) else CertificateEntry(Name=str(c))
            for c in as_list("Certifications", d.get("certifications", []))
        ],
        WorkExperiences=[
            WorkExperience(**w) if isinstance(w, dict) else WorkExperience(Title=str(w))
            for w in as_list("WorkExperiences", d.get("work_experiences", []))
        ],
        Education=[
            Education(**e) if isinstance(e, dict) else Education(Degree=str(e))
            for e in as_list("Education", d.get("education", []))
        ],
        TotalYearsOfExperience=int(d.get("TotalYearsOfExperience") or d.get("total_years_of_experience") or 0),
        PreferredJobTitles=[str(item) for item in as_list("PreferredJobTitles", d.get("preferred_job_titles", []))],
        PreferredLocations=[str(item) for item in as_list("PreferredLocations", d.get("preferred_locations", []))],
        TechnicalSkills=technical_skills,
    )
