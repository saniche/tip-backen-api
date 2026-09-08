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
    return UserProfile(
        Name=d["Name"],
        Email=d["Email"],
        Phone=d["Phone"],
        Location=d["Location"],
        LinkedIn=d.get("LinkedIn", ""),
        Summary=d["Summary"],
        SoftSkills=d["SoftSkills"],
        Languages=d["Languages"],
        Certifications=[CertificateEntry(**c) for c in d["Certifications"]],
        WorkExperiences=[WorkExperience(**w) for w in d["WorkExperiences"]],
        Education=[Education(**e) for e in d["Education"]],
        TotalYearsOfExperience=d["TotalYearsOfExperience"],
        PreferredJobTitles=d["PreferredJobTitles"],
        PreferredLocations=d["PreferredLocations"],
        TechnicalSkills=[SkillEntry(**s) for s in d["TechnicalSkills"]],
    )
