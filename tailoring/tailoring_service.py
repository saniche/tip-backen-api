"""Plan and generate the documents of one tailoring request (CV and optional cover letter)."""

from dataclasses import dataclass

from cover_letter.cover_letter_tailoring import build_cover_letter
from cover_letter.cover_letter_writer import render_cover_letter_markdown, suggest_cover_letter_filename
from cv.cv_tailoring import build_tailored_cv
from cv.job_group import merge_jobs
from cv.markdown_writer import render_tailored_cv_markdown, suggest_filename

KIND_CV = "cv"
KIND_COVER_LETTER = "cover_letter"


@dataclass
class WorkItem:
    kind: str  # cv | cover_letter
    scope: str  # per_job | general
    jobs: list


@dataclass
class GeneratedDocument:
    content: str
    filename: str
    warning: str | None = None


def plan_work_items(
    jobs: list, cv_mode: str, cover_letter_enabled: bool, cover_letter_mode: str | None
) -> list[WorkItem]:
    """per_job -> one item per job; general -> a single item for the whole group."""
    items: list[WorkItem] = []

    def expand(kind: str, mode: str) -> None:
        if mode == "per_job":
            items.extend(WorkItem(kind, "per_job", [job]) for job in jobs)
        else:
            items.append(WorkItem(kind, "general", list(jobs)))

    expand(KIND_CV, cv_mode)
    if cover_letter_enabled:
        expand(KIND_COVER_LETTER, cover_letter_mode or "per_job")
    return items


async def generate_document(
    item: WorkItem,
    profile,
    output_language: str,
    style_reference: str | None,
    match_score: int | None,
) -> GeneratedDocument:
    merged = merge_jobs(item.jobs)
    if item.kind == KIND_CV:
        cv = await build_tailored_cv(profile, merged.data, match_score, output_language, style_reference)
        return GeneratedDocument(render_tailored_cv_markdown(cv, profile), suggest_filename(cv, profile))

    letter, warning = await build_cover_letter(profile, merged.data, output_language, style_reference)
    title = merged.data.title or ""
    return GeneratedDocument(
        render_cover_letter_markdown(letter, profile, title, merged.company),
        suggest_cover_letter_filename(profile, title, merged.company),
        warning,
    )
