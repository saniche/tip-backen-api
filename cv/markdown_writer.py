import re
import unicodedata


def slugify(text: str, fallback: str = "document", max_length: int = 60) -> str:
    """ASCII, filesystem/blob-safe slug (no slashes or spaces)."""
    normalized = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")[:max_length].strip("-")
    return slug or fallback


def contact_lines(profile) -> list[str]:
    """Deterministic header copied from the profile, one field per line (never LLM-written)."""
    if profile is None:
        return []
    lines: list[str] = []
    location = (getattr(profile, "Location", "") or "").strip()
    phone = (getattr(profile, "Phone", "") or "").strip()
    email = (getattr(profile, "Email", "") or "").strip()
    linkedin = (getattr(profile, "LinkedIn", "") or "").strip()
    if location:
        lines.append(location)
    if phone:
        digits = re.sub(r"[^\d+]", "", phone)
        lines.append(f"[{phone}](tel:{digits})" if digits else phone)
    if email:
        lines.append(f"<{email}>")
    if linkedin:
        url = linkedin if linkedin.startswith(("http://", "https://")) else f"https://{linkedin}"
        lines.append(f"[{linkedin}]({url})")
    return [f"{line}  " for line in lines]  # trailing double space = hard line break in markdown


def _section(title: str, items: list[str], *, bullets: bool = True) -> list[str]:
    items = [item.strip() for item in items or [] if item and item.strip()]
    if not items:
        return []
    body = [f"- {item}" for item in items] if bullets else [", ".join(items)]
    return ["", f"## {title}", *body]


def render_tailored_cv_markdown(cv, profile=None) -> str:
    name = (getattr(profile, "Name", "") or "").strip() if profile is not None else ""
    lines = [f"# {name or 'Tailored CV'}", *contact_lines(profile)]
    target_role = (getattr(cv, "target_role", "") or "").strip()
    if target_role:
        lines.extend(["", f"## {target_role}"])
    summary = (getattr(cv, "summary", "") or "").strip()
    if summary:
        lines.extend(["", summary])
    lines.extend(_section("Experience", getattr(cv, "experience", [])))
    lines.extend(_section("Education", getattr(cv, "education", [])))
    lines.extend(_section("Certifications", getattr(cv, "certifications", [])))
    lines.extend(_section("Skills", getattr(cv, "skills", []), bullets=False))
    return "\n".join(lines) + "\n"


def suggest_filename(cv, profile=None) -> str:
    role = slugify(getattr(cv, "target_role", "") or "", fallback="tailored-cv")
    name = slugify(getattr(profile, "Name", "") or "", fallback="") if profile is not None else ""
    return f"{name}-{role}-cv.md" if name else f"{role}.md"
