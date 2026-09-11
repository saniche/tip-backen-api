import re


def normalize_job_content(content: str) -> dict:
    lines = [line.strip() for line in (content or "").splitlines() if line.strip()]
    responsibilities = [line for line in lines[1:] if re.match(r"[-*]", line)]
    skill_names = sorted(
        {
            match.group(0)
            for match in re.finditer(r"\b(?:Python|FastAPI|SQL|PostgreSQL|Java|JavaScript|TypeScript|AWS|Azure)\b", content or "", re.I)
        }
    )
    return {
        "key_responsibilities": [item.lstrip("-* ") for item in responsibilities],
        "required": {"qualifications": [], "skills": skill_names},
        "desirable": {"qualifications": [], "skills": []},
        "technical_stack": skill_names,
    }