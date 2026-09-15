WEIGHTS = {
    "required_qualifications": 0.35,
    "required_skills": 0.40,
    "desirable_qualifications": 0.10,
    "desirable_skills": 0.10,
    "technical_stack": 0.05,
}
VALUES = {"yes": 1.0, "partial": 0.5, "no": 0.0}


def score_match(groups: dict[str, list[str | dict]]) -> dict:
    available = {name: items for name, items in groups.items() if items}
    total_weight = sum(WEIGHTS[name] for name in available)
    if not total_weight:
        return {"score": 0, "eligible": False, "breakdown": {}, "effective_weights": {}}
    breakdown = {}
    effective = {}
    for name, items in available.items():
        scores = [
            VALUES.get((item.get("result") if isinstance(item, dict) else str(item)).lower(), 0.0) for item in items
        ]
        group_score = sum(scores) / len(scores)
        effective[name] = WEIGHTS[name] / total_weight
        breakdown[name] = group_score
    overall = sum(breakdown[name] * effective[name] for name in breakdown)

    # Eligibility is separate from score:
    # - required_qualifications: strict, no partial credit — every item must be an exact "Yes".
    #   An empty/absent category is vacuously satisfied (nothing required, nothing to fail).
    # - required_skills: flexible — the averaged group score just needs to clear 70%.
    # - desirable_* and technical_stack never affect eligibility, only score.
    required_quals_items = groups.get("required_qualifications", [])
    all_required_quals_matched = all(
        VALUES.get((item.get("result") if isinstance(item, dict) else str(item)).lower(), 0.0) == 1.0
        for item in required_quals_items
    )
    required_skills_score = breakdown.get("required_skills")
    required_skills_ok = required_skills_score is None or required_skills_score >= 0.70

    return {
        "score": round(overall * 100),
        "eligible": all_required_quals_matched and required_skills_ok,
        "breakdown": breakdown,
        "effective_weights": effective,
    }
