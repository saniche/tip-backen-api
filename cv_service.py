def validate_cv_selection(matchings: list[dict], mode: str) -> None:
    if not matchings:
        raise ValueError("At least one matching result is required")
    if mode not in {"per_job", "group_all"}:
        raise ValueError("mode must be per_job or group_all")
    owners = {item.get("user_id") for item in matchings}
    if len(owners) != 1:
        raise ValueError("All matching results must belong to the same owner")


def validate_grounded_content(content: str, profile_text: str, job_text: str) -> None:
    if not content.strip():
        raise ValueError("Generated CV is empty")
    allowed_context = f"{profile_text} {job_text}".lower()
    for line in content.splitlines():
        if line.startswith("- ") and line[2:].strip().lower() not in allowed_context:
            raise ValueError("Generated CV contains unsupported information")