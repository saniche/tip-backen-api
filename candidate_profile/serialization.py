"""
Conversion helpers between the pipeline modules' dataclasses and plain dicts, for storing/loading
from the DB's JSON columns. dataclasses.asdict() handles the dataclass -> dict direction; the
reverse needs explicit reconstruction since asdict() flattens nested dataclasses into nested dicts.
"""

from dataclasses import asdict, fields

from candidate_profile.profile_builder import CertificateEntry, Education, SkillEntry, UserProfile, WorkExperience


def user_profile_to_dict(profile: UserProfile) -> dict:
    return asdict(profile)


def _get_case_insensitive(data: dict, *keys: str, default=None):
    for key in keys:
        if key in data:
            return data[key]
        folded_key = key.casefold()
        for data_key, value in data.items():
            if isinstance(data_key, str) and data_key.casefold() == folded_key:
                return value
    return default


def _dataclass_from_dict(model, data: dict):
    field_names = {field.name.casefold(): field.name for field in fields(model)}
    normalized = {}
    for key, value in data.items():
        field_name = field_names.get(key.casefold()) if isinstance(key, str) else None
        normalized_key = field_name or key
        if normalized_key not in normalized or key == normalized_key:
            normalized[normalized_key] = value
    return model(**normalized)


def dict_to_user_profile(d: dict) -> UserProfile:
    if not isinstance(d, dict):
        return UserProfile()

    raw_skills = _get_case_insensitive(d, "Skills", "TechnicalSkills", default=[])
    if isinstance(raw_skills, list):
        skills = [
            _dataclass_from_dict(SkillEntry, item) if isinstance(item, dict) else SkillEntry(Name=str(item))
            for item in raw_skills
        ]
    else:
        skills = [SkillEntry(Name=str(raw_skills))] if raw_skills else []

    def as_list(*keys: str) -> list:
        value = _get_case_insensitive(d, *keys, default=[])
        return value if isinstance(value, list) else [value] if value else []

    return UserProfile(
        Name=str(_get_case_insensitive(d, "Name", "name", default="") or ""),
        Email=str(_get_case_insensitive(d, "Email", "email", default="") or ""),
        Phone=str(_get_case_insensitive(d, "Phone", "phone", default="") or ""),
        Location=str(_get_case_insensitive(d, "Location", "location", default="") or ""),
        LinkedIn=str(_get_case_insensitive(d, "LinkedIn", "linkedin", default="") or ""),
        Summary=str(_get_case_insensitive(d, "Summary", "summary", default="") or ""),
        SoftSkills=[str(item) for item in as_list("SoftSkills", "soft_skills")],
        CoreCompetences=[str(item) for item in as_list("CoreCompetences", "core_competences")],
        AdditionalInformations=[str(item) for item in as_list("AdditionalInformations", "additional_informations")],
        Languages=[str(item) for item in as_list("Languages", "languages")],
        Certifications=[
            _dataclass_from_dict(CertificateEntry, item) if isinstance(item, dict) else CertificateEntry(Name=str(item))
            for item in as_list("Certifications", "certifications")
        ],
        WorkExperiences=[
            _dataclass_from_dict(WorkExperience, item) if isinstance(item, dict) else WorkExperience(Title=str(item))
            for item in as_list("WorkExperiences", "work_experiences")
        ],
        Education=[
            _dataclass_from_dict(Education, item) if isinstance(item, dict) else Education(Degree=str(item))
            for item in as_list("Education", "education")
        ],
        TotalYearsOfExperience=int(
            _get_case_insensitive(d, "TotalYearsOfExperience", "total_years_of_experience", default=0) or 0
        ),
        PreferredJobTitles=[str(item) for item in as_list("PreferredJobTitles", "preferred_job_titles")],
        PreferredLocations=[str(item) for item in as_list("PreferredLocations", "preferred_locations")],
        Skills=skills,
    )
