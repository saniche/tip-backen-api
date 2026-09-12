from dataclasses import dataclass, field
import re
from typing import Any

from pydantic import BaseModel, ConfigDict

from llm_structured import StructuredProviderError, call_openai_structured


@dataclass
class JobData:
    title: str | None = None
    required: dict[str, list[str]] | None = None
    desirable: dict[str, list[str]] | None = None
    technical_stack: list[str] = field(default_factory=list)
    key_responsibilities: list[str] = field(default_factory=list)
    company: str | None = None
    location: str | None = None
    salary: str | None = None
    url: str | None = None
    source: str | None = None
    summary: str | None = None


@dataclass
class LlmMatchOutput:
    required_qualifications: list[dict[str, Any]] = field(default_factory=list)
    required_skills: list[dict[str, Any]] = field(default_factory=list)
    desirable_qualifications: list[dict[str, Any]] = field(default_factory=list)
    desirable_skills: list[dict[str, Any]] = field(default_factory=list)
    technical_stack: list[dict[str, Any]] = field(default_factory=list)
    notes: str = ""


class MatchAssessmentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    result: str
    value: str
    rationale: str


class StructuredMatchOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    required_qualifications: list[MatchAssessmentOutput]
    required_skills: list[MatchAssessmentOutput]
    desirable_qualifications: list[MatchAssessmentOutput]
    desirable_skills: list[MatchAssessmentOutput]
    technical_stack: list[MatchAssessmentOutput]
    notes: str


MATCHING_SYSTEM_PROMPT = (
    "Compare the candidate profile with the job requirements. Assess every supplied requirement as Yes, Partial, or No. "
    "Ground each rationale in the supplied data and do not add unsupported credentials or experience. "
    "For Yes or Partial, cite evidence that is actually present in the candidate profile; do not treat the job requirement itself as evidence."
)


def _profile_evidence_terms(profile: Any) -> set[str]:
    if isinstance(profile, dict):
        values = profile.values()
    elif isinstance(profile, (list, tuple, set)):
        values = profile
    else:
        values = (profile,)
    terms: set[str] = set()
    for value in values:
        if isinstance(value, (dict, list, tuple, set)):
            terms.update(_profile_evidence_terms(value))
        elif value is not None:
            terms.update(re.findall(r"[a-z0-9]+", str(value).lower()))
    return terms


def _validate_assessments(data: dict[str, Any], profile: dict[str, Any], job: JobData) -> None:
    expected = {
        "required_qualifications": (job.required or {}).get("qualifications", []),
        "required_skills": (job.required or {}).get("skills", []),
        "desirable_qualifications": (job.desirable or {}).get("qualifications", []),
        "desirable_skills": (job.desirable or {}).get("skills", []),
        "technical_stack": job.technical_stack or [],
    }
    profile_text = str(profile).lower()
    profile_evidence_terms = _profile_evidence_terms(profile)
    allowed_rationale_words = {"profile", "contains", "requirement", "evidence", "related", "matching", "not", "found", "no"}
    for group, values in expected.items():
        assessments = data[group]
        expected_values = [str(value) for value in values]
        if [item["value"] for item in assessments] != expected_values:
            raise StructuredProviderError(f"Matching output does not cover {group}")
        for item in assessments:
            if item["result"] not in {"Yes", "Partial", "No"}:
                raise StructuredProviderError("Matching output contains an invalid assessment result")
            if item["result"] in {"Yes", "Partial"}:
                requirement_terms = set(re.findall(r"[a-z0-9]+", item["value"].lower()))
                if not requirement_terms.intersection(profile_evidence_terms):
                    raise StructuredProviderError("Matching output lacks profile evidence")
            rationale_words = {word.strip(".,;:!?()[]{}'") for word in item["rationale"].lower().split()}
            allowed_words = allowed_rationale_words | {word.lower() for word in item["value"].split()}
            if any(len(word) > 3 and word not in profile_text and word not in allowed_words for word in rationale_words):
                raise StructuredProviderError("Matching output contains an unsupported rationale")


async def get_llm_match_output(profile: dict[str, Any], job: JobData) -> LlmMatchOutput:
    context = {"profile": profile, "job": job.__dict__}
    output = await call_openai_structured(
        MATCHING_SYSTEM_PROMPT, str(context), StructuredMatchOutput, operation="job_matching"
    )
    data = output.model_dump()
    _validate_assessments(data, profile, job)
    return LlmMatchOutput(**data)
