"""Merge several job postings into one synthetic posting for 'general' (group) tailoring.

The CV/cover-letter LLM contract takes a single job, so a group is collapsed in code: requirement
lists become a union ranked by how many postings ask for each item (the most shared first), and
the title joins the distinct titles. A single-job group is returned unchanged.
"""

from collections import Counter
from dataclasses import dataclass

from matching.llm_matching import JobData

MAX_ITEMS_PER_LIST = 30
_GROUPS = ("qualifications", "skills")


@dataclass
class MergedJob:
    data: JobData
    company: str | None
    titles: list[str]


def _clean(values) -> list[str]:
    return [str(v).strip() for v in (values or []) if str(v).strip()]


def _ranked_union(lists: list[list[str]], limit: int = MAX_ITEMS_PER_LIST) -> list[str]:
    counts: Counter[str] = Counter()
    first_seen: dict[str, str] = {}
    for items in lists:
        for key in {item.casefold() for item in items}:
            counts[key] += 1
        for item in items:
            first_seen.setdefault(item.casefold(), item)
    order = {key: index for index, key in enumerate(first_seen)}
    ranked = sorted(counts, key=lambda key: (-counts[key], order[key]))
    return [first_seen[key] for key in ranked[:limit]]


def _as_groups(value) -> dict[str, list[str]]:
    if isinstance(value, dict):
        return {name: _clean(value.get(name)) for name in _GROUPS}
    return {"qualifications": [], "skills": _clean(value)}


def _merge_requirements(values: list) -> dict | list | None:
    if all(isinstance(v, list) or v is None for v in values):
        return _ranked_union([_clean(v) for v in values]) or None
    grouped = [_as_groups(v) for v in values]
    return {name: _ranked_union([g[name] for g in grouped]) for name in _GROUPS}


def _job_to_data(job) -> JobData:
    return JobData(
        title=job.title,
        required=job.required,
        desirable=job.desirable,
        tools_and_technologies=list(job.tools_and_technologies or []),
        key_responsibilities=list(job.key_responsibilities or []),
        summary=job.summary,
        company=job.company,
        location=job.location,
    )


def merge_jobs(jobs: list) -> MergedJob:
    if not jobs:
        raise ValueError("At least one job is required")
    if len(jobs) == 1:
        return MergedJob(data=_job_to_data(jobs[0]), company=jobs[0].company, titles=[jobs[0].title])

    titles = list(dict.fromkeys(job.title for job in jobs if job.title))
    companies = {job.company for job in jobs if job.company}
    data = JobData(
        title=" / ".join(titles),
        required=_merge_requirements([job.required for job in jobs]),
        desirable=_merge_requirements([job.desirable for job in jobs]),
        tools_and_technologies=_ranked_union([_clean(job.tools_and_technologies) for job in jobs]),
        key_responsibilities=_ranked_union([_clean(job.key_responsibilities) for job in jobs], limit=20),
        # Per-posting summaries cannot be quoted as one evidence phrase, so a group has none.
        summary=None,
        company=next(iter(companies)) if len(companies) == 1 else None,
    )
    return MergedJob(data=data, company=data.company, titles=titles)
