import json
from dataclasses import asdict, dataclass, field

from pydantic import BaseModel, ConfigDict

from profile.serialization import user_profile_to_dict
from shared.grounding import unsupported_terms
from shared.llm_structured import call_openai_structured


class GroundingError(ValueError):
    """The generated CV contains content that is not backed by the profile or job."""


@dataclass
class TailoredCv:
    target_role: str = ""
    summary: str = ""
    experience: list[str] = field(default_factory=list)
    education: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)


class TailoredExperienceOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_index: int
    title: str
    company: str | None
    start_date: str | None
    end_date: str | None
    summary: str | None = None
    descriptions: list[str]
    description_evidence: list[list[str]]


class TailoredCvOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_role: str
    summary: str
    experience: list[TailoredExperienceOutput]
    education: list[str]
    certifications: list[str]
    skills: list[str]
    education_evidence: list[list[str]]
    certification_evidence: list[list[str]]


CV_TAILORING_SYSTEM_PROMPT = (
    "Write a tailored CV using only the supplied profile and job, and use a match score only when "
    "a numeric score is supplied. Never infer or invent a missing score. "
    "Do not invent facts. Use empty arrays for unavailable sections and write in the requested language. "
    "List skills only when they appear in the profile's Skills or SoftSkills; job requirements alone "
    "are not evidence of the candidate's skills. "
    "For each experience, use profile_index as the zero-based index of its source in "
    "profile.WorkExperiences. Copy company, start_date, and end_date exactly from that entry's "
    "Company, StartDate, and EndDate, including null values. The experience title may be tailored. "
    "An experience summary is optional: when useful, write one sentence based only on that "
    "experience's Summary and RealisationDescription, alongside its descriptions. "
    "If both fields have no responsibility details, set summary to null and descriptions to an empty list. "
    "Provide description_evidence for each experience description using complete source fields "
    "from that same profile experience. Provide education_evidence and certification_evidence "
    "for each item using complete source fields from the corresponding profile section. "
    "Evidence must contain only the exact field value, without its field name or surrounding quotes. "
    "Reuse the wording of cited sources closely in descriptions; do not add unsupported numbers, "
    "seniority, leadership or employer claims."
)

STYLE_REFERENCE_ADDENDUM = (
    " A style_reference document is supplied. Use it ONLY to match tone, voice, sentence length and "
    "phrasing style. Do not reuse any fact, employer, date, number or achievement from it; every fact "
    "must still come from the profile. Do not stray far from its register."
)
MAX_STYLE_REFERENCE_CHARS = 6000


def _source_values(profile) -> tuple[set[str], set[str]]:
    education_sources = {
        value
        for item in getattr(profile, "Education", []) or []
        for value in (
            getattr(item, "Degree", None),
            getattr(item, "Institution", None),
            getattr(item, "Field", None),
            getattr(item, "Year", None),
            getattr(item, "Location", None),
            "Completed"
            if getattr(item, "Completed", None) is True
            else "Not completed"
            if getattr(item, "Completed", None) is False
            else None,
        )
        if value
    }
    certification_sources = {
        value
        for item in getattr(profile, "Certifications", []) or []
        for value in (item.Name, item.Issuer, item.Year)
        if value
    }
    return education_sources, certification_sources


def _validate_evidence(values: list[str], sources: set[str], field_name: str) -> None:
    if not values:
        raise GroundingError(f"Tailored CV contains unsupported {field_name} evidence: no evidence provided")
    unsupported = [value for value in values if value not in sources]
    if unsupported:
        raise GroundingError(f"Tailored CV contains unsupported {field_name} evidence: {unsupported!r}")


def _validate_claim_against_evidence(value: str, evidence: list[str], field_name: str) -> None:
    unsupported = unsupported_terms(value, evidence)
    if unsupported:
        details = ", ".join(sorted(unsupported)[:5])
        raise GroundingError(f"Tailored CV contains unsupported {field_name} content: {details}")


def _validate_section_evidence(items: list[str], evidence: list[list[str]], sources: set[str], field_name: str) -> None:
    if len(items) != len(evidence):
        raise GroundingError(
            f"Tailored CV {field_name} evidence does not match generated items: "
            f"{len(items)} items, {len(evidence)} evidence lists"
        )
    for index, (item, item_evidence) in enumerate(zip(items, evidence, strict=True)):
        label = f"{field_name} item {index}"
        _validate_evidence(item_evidence, sources, label)
        _validate_claim_against_evidence(item, item_evidence, label)


def _validate_grounded_content(output: TailoredCvOutput, profile, job_data) -> None:
    education_sources, certification_sources = _source_values(profile)
    if output.target_role != (getattr(job_data, "title", None) or ""):
        raise GroundingError(f"Tailored CV contains an unsupported target role: {output.target_role!r}")
    experiences = getattr(profile, "WorkExperiences", []) or []
    for item in output.experience:
        if item.profile_index < 0 or item.profile_index >= len(experiences):
            raise GroundingError(f"Tailored CV has invalid experience profile_index: {item.profile_index}")
        source = experiences[item.profile_index]
        for field_name, source_name in (
            ("company", "Company"), ("start_date", "StartDate"), ("end_date", "EndDate")
        ):
            value = getattr(item, field_name)
            expected = getattr(source, source_name)
            if value != expected:
                raise GroundingError(
                    f"Tailored CV experience {field_name} does not match profile index "
                    f"{item.profile_index}: received {value!r}, expected {expected!r}"
                )
        has_responsibilities = any(
            value and value.strip()
            for value in (source.Summary, *(source.RealisationDescription or []))
        )
        if not has_responsibilities and ((item.summary and item.summary.strip()) or item.descriptions):
            raise GroundingError(
                f"Tailored CV experience at profile index {item.profile_index} has "
                "no responsibility details to support a summary or descriptions"
            )
        source_fields = {
            "Summary": source.Summary,
            "Title": source.Title,
            "Company": source.Company,
            "StartDate": source.StartDate,
            "EndDate": source.EndDate,
        }
        experience_sources = {value for value in source_fields.values() if value}
        experience_sources.update(value for value in (source.RealisationDescription or []) if value)
        field_representations = {
            f"{name}={value!r}": value for name, value in source_fields.items() if value
        }
        field_representations.update(
            (f"RealisationDescription={value!r}", value)
            for value in (source.RealisationDescription or []) if value
        )
        evidence = [
            [
                value if value in experience_sources else field_representations.get(value, value)
                for value in item_evidence
            ]
            for item_evidence in item.description_evidence
        ]
        _validate_section_evidence(
            item.descriptions, evidence, experience_sources,
            f"experience at profile index {item.profile_index}",
        )
    _validate_section_evidence(output.education, output.education_evidence, education_sources, "education")
    _validate_section_evidence(output.certifications, output.certification_evidence, certification_sources, "certifications")


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

    last_error: GroundingError | None = None
    for attempt in range(2):
        attempt_context = dict(context)
        if last_error is not None:
            attempt_context["validation_feedback"] = (
                f"Your previous answer was rejected: {last_error}. Fix it by reusing the cited source wording."
            )
        output = await call_openai_structured(
            system_prompt, json.dumps(attempt_context, ensure_ascii=False), TailoredCvOutput, operation="cv_tailoring"
        )
        try:
            _validate_grounded_content(output, profile, job_data)
        except GroundingError as exc:
            last_error = exc
            continue
        experience = []
        for item in output.experience:
            dates = " - ".join(value for value in (item.start_date, item.end_date) if value)
            header = " | ".join(value for value in (item.title, item.company, dates) if value)
            if header:
                experience.append(header)
            if item.summary and item.summary.strip():
                experience.append(item.summary)
            experience.extend(item.descriptions)
        return TailoredCv(
            experience=experience,
            **output.model_dump(exclude={"experience", "education_evidence", "certification_evidence"})
        )
    raise last_error
