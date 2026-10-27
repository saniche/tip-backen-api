import json
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator

from shared.llm_structured import StructuredProviderError, call_openai_structured


@dataclass
class JobData:
    title: str | None = None
    required: dict[str, list[str]] | list[str] | None = None
    desirable: dict[str, list[str]] | list[str] | None = None
    tools_and_technologies: list[str] = field(default_factory=list)
    key_responsibilities: list[str] = field(default_factory=list)
    company: str | None = None
    location: str | None = None
    salary: str | None = None
    url: str | None = None
    source: str | None = None
    summary: str | None = None


@dataclass(frozen=True)
class MatchingCriteria:
    requirements: list[str]
    desirables: list[str]
    required_qualifications: list[str]
    required_skills: list[str]


def _criteria_groups(value: dict[str, Any] | list[str] | None, category: str) -> tuple[list[str], list[str]]:
    if value is None:
        return [], []
    if isinstance(value, list):
        if any(not isinstance(item, str) for item in value):
            raise StructuredProviderError(f"Matching input contains a non-string {category} criterion.")
        return [], list(value)
    if not isinstance(value, dict):
        raise StructuredProviderError(f"Matching input contains an invalid {category} structure.")

    qualifications = value.get("qualifications", []) or []
    skills = value.get("skills", []) or []
    if not isinstance(qualifications, list) or not isinstance(skills, list):
        raise StructuredProviderError(f"Matching input contains an invalid {category} structure.")
    if any(not isinstance(item, str) for item in [*qualifications, *skills]):
        raise StructuredProviderError(f"Matching input contains a non-string {category} criterion.")
    return list(qualifications), list(skills)


def matching_criteria(job: JobData) -> MatchingCriteria:
    required_qualifications, required_skills = _criteria_groups(job.required, "requirement")
    desirable_qualifications, desirable_skills = _criteria_groups(job.desirable, "desirable")
    return MatchingCriteria(
        requirements=[*required_qualifications, *required_skills],
        desirables=[*desirable_qualifications, *desirable_skills],
        required_qualifications=required_qualifications,
        required_skills=required_skills,
    )


def _non_empty(value: str) -> str:
    if not value.strip():
        raise ValueError("String fields must not be empty or whitespace-only.")
    return value


class ItemMatching(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    criterion: str
    judgment: Literal["Yes", "No"]
    evidence: str

    @field_validator("criterion", "evidence")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        return _non_empty(value)


class MatchAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    eligibility: str
    matching: str
    chance_of_success: str

    @field_validator("eligibility", "matching", "chance_of_success")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        return _non_empty(value)


class LlmMatchOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    requirements: list[ItemMatching]
    desirables: list[ItemMatching]
    notes: str
    analysis: MatchAnalysis

    @field_validator("notes")
    @classmethod
    def validate_notes_non_empty(cls, value: str) -> str:
        return _non_empty(value)


MATCHING_SYSTEM_PROMPT = """\
You are an expert career counselor, recruiter, and job-matching specialist. Evaluate the candidate's fit for the job posting using semantic understanding and evidence-based reasoning.

Output rules
- The input contains `criteria_to_assess.requirements` and `criteria_to_assess.desirables`. Assess every entry in each list, in order, using the entry text as `criterion`. If an entry bundles several distinct items, you may split it into separate items (keeping the original order); never skip an entry. Return an empty list only when the input list is empty.
- Return only the exact structured response schema provided, with no additional fields, Markdown, or prose outside the schema.
- For each criterion, return `Yes` only when the candidate profile provides sufficient supporting evidence; otherwise, return `No`.
- Treat equivalent terms, synonyms, abbreviations, alternate spellings, and equivalent job titles for the same role and seniority as matches (e.g., C# and CSharp, RN and Registered Nurse, CPA and Certified Public Accountant, or Sales Representative and Sales Rep).
- Do not infer skills or qualifications from related experience or plausible assumptions. Count years of experience only when explicitly stated or directly computable from profile dates.
- Provide concise, profile-based evidence for every criterion, explaining why it is met or what evidence is missing or insufficient.
- Treat `tools_and_technologies` and `key_responsibilities` as context only; do not use them for scoring.

Evaluation priorities
- Required and desirable qualifications, skills, and credentials
- Experience level and duration
- Industry and domain expertise
- Alignment with job responsibilities

Narrative fields
For `eligibility`, `matching`, and `chance_of_success`:
- Provide a concise, non-empty analysis grounded in the available evidence.
- Identify uncertainties about mandatory requirements that cannot be verified, including licenses, certifications, work authorization, and education.
- Avoid guaranteeing hiring outcomes.
- Do not include numeric scores.
"""


def _validate_assessments(output: LlmMatchOutput, expected: MatchingCriteria) -> None:
    for category, actual, expected_criteria in (
        ("requirements", output.requirements, expected.requirements),
        ("desirables", output.desirables, expected.desirables),
    ):
        # Splitting or rewording criteria is tolerated; only a category with no assessments is rejected.
        if expected_criteria and not actual:
            raise StructuredProviderError(
                f"Matching output does not cover {category}: "
                f"expected {len(expected_criteria)} items, got 0."
            )


async def get_llm_match_output(profile: dict[str, Any], job: JobData) -> LlmMatchOutput:
    criteria = matching_criteria(job)
    context = {
        "profile": profile,
        "job": job.__dict__,
        "criteria_to_assess": {
            "requirements": list(criteria.requirements),
            "desirables": list(criteria.desirables),
        },
    }
    output = await call_openai_structured(
        MATCHING_SYSTEM_PROMPT,
        json.dumps(context, ensure_ascii=False, default=str),
        LlmMatchOutput,
        operation="job_matching",
    )
    _validate_assessments(output, criteria)
    return output
