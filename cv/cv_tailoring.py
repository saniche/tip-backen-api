import json
import logging
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, StrictInt

from candidate_profile.serialization import user_profile_to_dict
from shared.llm_structured import call_openai_structured

logger = logging.getLogger("tip-api")


class EmptyExperienceError(ValueError):
    """A tailored CV cannot be produced without an experience entry."""


@dataclass
class TailoredExperience:
    company: str | None = None
    location: str | None = None
    title: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    summary: str | None = None
    descriptions: list[str] = field(default_factory=list)


@dataclass
class TailoredCv:
    target_role: str = ""
    summary: str = ""
    experience: list[TailoredExperience | str] = field(default_factory=list)
    education: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)


class TailoredExperienceOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_index: StrictInt | None = None
    title: str
    company: str | None
    start_date: str | None
    end_date: str | None
    summary: str | None = None
    descriptions: list[str]


class TailoredEducationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_index: StrictInt | None = None
    degree: str | None
    institution: str | None
    year: str | None


class TailoredCvOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_role: str
    summary: str
    experience: list[TailoredExperienceOutput]
    education: list[TailoredEducationOutput]
    certifications: list[str]
    skills: list[str]


CV_TAILORING_SYSTEM_PROMPT = (
    "Write a tailored CV using only the supplied profile and job, and use a match score only when "
    "a numeric score is supplied. Never infer or invent a missing score. "
    "Do not invent facts. Use empty arrays for unavailable sections and write in the requested language. "
    "List skills only when they appear in the profile's Skills or SoftSkills; job requirements alone "
    "are not evidence of the candidate's skills. "
    "For each experience, use profile_index as the zero-based index of its source in "
    "profile.WorkExperiences. Copy company, start_date, and end_date from that entry's "
    "Company, StartDate, and EndDate, including null values. The experience title may be tailored. "
    "For each education entry, use profile_index as the zero-based index of its source in "
    "profile.Education and copy Degree, Institution, and Year into degree, institution, and year. "
    "Write a useful experience summary and descriptions using the experience's available details. "
    "Write descriptions in the requested language without adding facts. "
    "Do not add unsupported numbers, seniority, leadership or employer claims."
)

STYLE_REFERENCE_ADDENDUM = (
    " A style_reference document is supplied. Use it ONLY to match tone, voice, sentence length and "
    "phrasing style. Do not reuse any fact, employer, date, number or achievement from it; every fact "
    "must still come from the profile. Do not stray far from its register."
)
MAX_STYLE_REFERENCE_CHARS = 6000


def _normalized(value: str | None) -> str | None:
    if value is None:
        return None
    text = unicodedata.normalize("NFKD", value.casefold())
    return " ".join("".join(char for char in text if not unicodedata.combining(char)).split())


def _warn_mismatches(item, source, fields: tuple[tuple[str, str], ...], section: str) -> None:
    for output_field, source_field in fields:
        actual = getattr(item, output_field)
        expected = getattr(source, source_field)
        differs = actual != expected if output_field == "year" else _normalized(actual) != _normalized(expected)
        if differs:
            logger.warning(
                "Tailored CV %s field %s differs from profile at index %s; using profile value",
                section,
                output_field,
                item.profile_index,
            )


def _invalid_indexes(output: TailoredCvOutput, profile) -> list[str]:
    invalid = []
    for section, entries, sources in (
        ("experience", output.experience, getattr(profile, "WorkExperiences", []) or []),
        ("education", output.education, getattr(profile, "Education", []) or []),
    ):
        for position, item in enumerate(entries):
            index = item.profile_index
            if index is None or index < 0 or index >= len(sources):
                invalid.append(
                    f"{section} entry {position}: profile_index {index!r} (valid range 0..{len(sources) - 1})"
                )
    return invalid


Entry = TypeVar("Entry", TailoredExperienceOutput, TailoredEducationOutput)


def _valid_entries(entries: list[Entry], source_count: int, section: str) -> list[Entry]:
    result: list[Entry] = []
    seen: set[int] = set()
    for item in entries:
        index = item.profile_index
        if index is None or index < 0 or index >= source_count:
            logger.warning("Dropping tailored CV %s entry with invalid profile index", section)
        elif index in seen:
            logger.warning("Dropping duplicate tailored CV %s profile index %s", section, index)
        else:
            seen.add(index)
            result.append(item)
    return result


async def build_tailored_cv(
    profile,
    job_data,
    match_score: int | None,
    output_language: str = "English",
    style_reference: str | None = None,
) -> TailoredCv:
    profile_context = user_profile_to_dict(profile)
    profile_context.pop("CoreCompetences", None)
    profile_context.pop("AdditionalInformations", None)
    context = {
        "profile": profile_context,
        "job": asdict(job_data),
        "output_language": output_language,
    }
    if match_score is not None:
        context["match_score"] = match_score
    system_prompt = CV_TAILORING_SYSTEM_PROMPT
    if style_reference and style_reference.strip():
        context["style_reference"] = style_reference.strip()[:MAX_STYLE_REFERENCE_CHARS]
        system_prompt += STYLE_REFERENCE_ADDENDUM

    feedback = None
    for attempt in range(2):
        attempt_context = dict(context)
        if feedback:
            attempt_context["validation_feedback"] = feedback
        output = await call_openai_structured(
            system_prompt, json.dumps(attempt_context, ensure_ascii=False), TailoredCvOutput, operation="cv_tailoring"
        )
        invalid = _invalid_indexes(output, profile)
        if not invalid or attempt == 1:
            break
        feedback = "Use valid profile indexes for these entries: " + "; ".join(invalid)

    experiences = getattr(profile, "WorkExperiences", []) or []
    educations = getattr(profile, "Education", []) or []
    experience = []
    for item in _valid_entries(output.experience, len(experiences), "experience"):
        assert item.profile_index is not None
        source = experiences[item.profile_index]
        _warn_mismatches(
            item, source, (("company", "Company"), ("start_date", "StartDate"), ("end_date", "EndDate")),
            "experience",
        )
        experience.append(
            TailoredExperience(
                company=source.Company,
                location=source.Location,
                title=item.title,
                start_date=source.StartDate,
                end_date=source.EndDate,
                summary=item.summary,
                descriptions=item.descriptions,
            )
        )
    education = []
    for item in _valid_entries(output.education, len(educations), "education"):
        assert item.profile_index is not None
        source = educations[item.profile_index]
        _warn_mismatches(
            item, source, (("degree", "Degree"), ("institution", "Institution"), ("year", "Year")), "education"
        )
        rendered = ", ".join(
            value for value in (source.Degree, source.Institution, source.Year) if value and value.strip()
        )
        if rendered:
            education.append(rendered)
    if not experience:
        raise EmptyExperienceError("The generated CV has no valid experience entries.")
    if not education:
        logger.warning("Tailored CV has no education entries")
    return TailoredCv(
        target_role=getattr(job_data, "title", None) or "",
        summary=output.summary,
        experience=experience,
        education=education,
        certifications=output.certifications,
        skills=output.skills,
    )
