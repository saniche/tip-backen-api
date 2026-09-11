from dataclasses import dataclass, field


@dataclass
class TailoredCv:
    target_role: str = ""
    summary: str = ""
    experience: list[str] = field(default_factory=list)
    education: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)


def build_tailored_cv(profile, job_data, match_score: int, output_language: str = "English") -> TailoredCv:
    skills = list(getattr(profile, "TechnicalSkills", []) or [])
    skill_names = [str(item.Name if hasattr(item, "Name") else item) for item in skills]
    return TailoredCv(
        target_role=job_data.title or "Target Role",
        summary=(
            f"Tailored for {job_data.title or 'target role'} using the current profile "
            f"and a match score of {match_score}."
        ),
        experience=[
            f"{item.Title or 'Experience'} at {item.Company or 'previous employer'}"
            for item in getattr(profile, "WorkExperiences", []) or []
        ],
        education=[
            str(item.Degree or item.Institution or "Education") for item in getattr(profile, "Education", []) or []
        ],
        certifications=[str(item.Name or "Certification") for item in getattr(profile, "Certifications", []) or []],
        skills=skill_names[:12],
    )
