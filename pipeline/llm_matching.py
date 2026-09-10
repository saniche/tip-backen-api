from dataclasses import dataclass, field
from typing import Any


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


def get_llm_match_output(profile: dict[str, Any], job: JobData) -> LlmMatchOutput:
    def map_items(items: list[str] | None) -> list[dict[str, Any]]:
        return [{"result": "Yes", "value": item} for item in (items or [])]

    return LlmMatchOutput(
        required_qualifications=map_items(job.required.get("qualifications") if job.required else []),
        required_skills=map_items(job.required.get("skills") if job.required else []),
        desirable_qualifications=map_items(job.desirable.get("qualifications") if job.desirable else []),
        desirable_skills=map_items(job.desirable.get("skills") if job.desirable else []),
        technical_stack=[{"result": "Yes", "value": item} for item in (job.technical_stack or [])],
        notes=f"Profile {profile.get('Name', '')} matched job {job.title or 'target'}.",
    )
