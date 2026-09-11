def render_tailored_cv_markdown(cv) -> str:
    lines = [
        "# Tailored CV",
        "",
        f"**Target role:** {getattr(cv, 'target_role', '')}",
        "",
        "## Summary",
        getattr(cv, "summary", ""),
        "",
        "## Experience",
    ]
    for item in getattr(cv, "experience", []) or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Education"])
    for item in getattr(cv, "education", []) or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Certifications"])
    for item in getattr(cv, "certifications", []) or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Skills"])
    for item in getattr(cv, "skills", []) or []:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def suggest_filename(cv) -> str:
    title = getattr(cv, "target_role", "tailored-cv").strip().lower().replace(" ", "-")
    return f"{title or 'tailored-cv'}.md"
