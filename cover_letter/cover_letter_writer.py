from datetime import date

from cv.markdown_writer import contact_lines, slugify


def render_cover_letter_markdown(
    letter, profile, job_title: str, company: str | None, today: date | None = None
) -> str:
    name = (getattr(profile, "Name", "") or "").strip() if profile is not None else ""
    lines = [f"# {name or 'Cover Letter'}", *contact_lines(profile), "", (today or date.today()).isoformat(), ""]
    lines.append(f"Hiring Team, {company}" if company else "Hiring Team")
    if job_title:
        lines.extend(["", f"**Re: {job_title}**"])
    lines.extend(["", letter.greeting.strip()])
    for paragraph in letter.paragraphs:
        if paragraph.strip():
            lines.extend(["", paragraph.strip()])
    lines.extend(["", letter.closing.strip()])
    if name:
        lines.append(name)
    return "\n".join(lines) + "\n"


def suggest_cover_letter_filename(profile, job_title: str, company: str | None) -> str:
    name = slugify(getattr(profile, "Name", "") or "", fallback="") if profile is not None else ""
    target = slugify(company or job_title or "", fallback="")
    parts = [part for part in (name, target, "cover-letter") if part]
    return "-".join(parts) + ".md"
