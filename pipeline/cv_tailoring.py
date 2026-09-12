from dataclasses import dataclass, field
import re

from pydantic import BaseModel, ConfigDict

from llm_structured import call_openai_structured


@dataclass
class TailoredCv:
    target_role: str = ""
    summary: str = ""
    experience: list[str] = field(default_factory=list)
    education: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)


class TailoredCvOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_role: str
    summary: str
    experience: list[str]
    education: list[str]
    certifications: list[str]
    skills: list[str]
    summary_evidence: list[str]
    experience_evidence: list[list[str]]
    education_evidence: list[list[str]]
    certification_evidence: list[list[str]]


CV_TAILORING_SYSTEM_PROMPT = (
    "Write a tailored CV using only the supplied profile, job, and match score. "
    "Do not invent facts. Use empty arrays for unavailable sections and write in the requested language. "
    "For every generated summary, experience, education, and certification item, populate "
    "summary_evidence, experience_evidence, education_evidence, and certification_evidence "
    "with exact source phrases from the supplied profile or job context."
)


def _source_values(profile, job_data) -> tuple[set[str], set[str], set[str], set[str], set[str]]:
    profile_skills = {
        str(item.Name if hasattr(item, "Name") else item).strip().lower()
        for item in getattr(profile, "TechnicalSkills", []) or []
    }
    job_skills = {str(item).strip().lower() for item in getattr(job_data, "technical_stack", []) or []}
    summary_sources = {value for value in (getattr(profile, "Summary", ""), getattr(job_data, "summary", ""), getattr(job_data, "title", "")) if value}
    experience_sources = {
        value
        for item in getattr(profile, "WorkExperiences", []) or []
        for value in (item.Summary, item.Title, item.Company)
        if value
    }
    education_sources = {
        value
        for item in getattr(profile, "Education", []) or []
        for value in (item.Degree, item.Institution, item.Field, item.Year)
        if value
    }
    certification_sources = {
        value
        for item in getattr(profile, "Certifications", []) or []
        for value in (item.Name, item.Issuer, item.Year)
        if value
    }
    return profile_skills | job_skills, summary_sources, experience_sources, education_sources, certification_sources


def _validate_evidence(values: list[str], sources: set[str], field_name: str) -> None:
    if not values or any(value not in sources for value in values):
        raise ValueError(f"Tailored CV contains unsupported {field_name} evidence")


def _validate_claim_against_evidence(value: str, evidence: list[str], field_name: str) -> None:
    evidence_words = set(re.findall(r"\w+", " ".join(evidence).lower()))
    neutral_words = {"tailored", "profile", "candidate", "target", "role", "resume", "curriculum", "vitae", "experience"}
    unsupported = {
        word for word in re.findall(r"\w+", value.lower()) if len(word) > 3 and word not in evidence_words | neutral_words
    }
    if unsupported:
        raise ValueError(f"Tailored CV contains unsupported {field_name} content")


def _validate_section_evidence(items: list[str], evidence: list[list[str]], sources: set[str], field_name: str) -> None:
    if len(items) != len(evidence):
        raise ValueError(f"Tailored CV {field_name} evidence does not match generated items")
    for item, item_evidence in zip(items, evidence, strict=True):
        _validate_evidence(item_evidence, sources, field_name)
        _validate_claim_against_evidence(item, item_evidence, field_name)


def _validate_grounded_content(output: TailoredCvOutput, profile, job_data) -> None:
    supported_skills, summary_sources, experience_sources, education_sources, certification_sources = _source_values(profile, job_data)
    if any(skill.strip().lower() not in supported_skills for skill in output.skills):
        raise ValueError("Tailored CV contains unsupported skills")
    if output.target_role != (getattr(job_data, "title", None) or ""):
        raise ValueError("Tailored CV contains an unsupported target role")
    _validate_evidence(output.summary_evidence, summary_sources, "summary")
    _validate_claim_against_evidence(output.summary, output.summary_evidence, "summary")
    _validate_section_evidence(output.experience, output.experience_evidence, experience_sources, "experience")
    _validate_section_evidence(output.education, output.education_evidence, education_sources, "education")
    _validate_section_evidence(output.certifications, output.certification_evidence, certification_sources, "certifications")


async def build_tailored_cv(profile, job_data, match_score: int, output_language: str = "English") -> TailoredCv:
    context = {
        "profile": getattr(profile, "__dict__", {}),
        "job": getattr(job_data, "__dict__", {}),
        "match_score": match_score,
        "output_language": output_language,
    }
    output = await call_openai_structured(
        CV_TAILORING_SYSTEM_PROMPT, str(context), TailoredCvOutput, operation="cv_tailoring"
    )
    _validate_grounded_content(output, profile, job_data)
    return TailoredCv(**output.model_dump(exclude={"summary_evidence", "experience_evidence", "education_evidence", "certification_evidence"}))
