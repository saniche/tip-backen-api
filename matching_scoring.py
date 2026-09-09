WEIGHTS = {"required_qualifications": 0.35, "required_skills": 0.40, "desirable_qualifications": 0.10, "desirable_skills": 0.10, "technical_stack": 0.05}
VALUES = {"yes": 1.0, "partial": 0.5, "no": 0.0}


def score_match(groups: dict[str, list[str | dict]]) -> dict:
    available = {name: items for name, items in groups.items() if items}
    total_weight = sum(WEIGHTS[name] for name in available)
    if not total_weight:
        return {"score": 0, "eligible": False, "breakdown": {}, "effective_weights": {}}
    breakdown = {}
    effective = {}
    for name, items in available.items():
        scores = [VALUES.get((item.get("result") if isinstance(item, dict) else str(item)).lower(), 0.0) for item in items]
        group_score = sum(scores) / len(scores)
        effective[name] = WEIGHTS[name] / total_weight
        breakdown[name] = group_score
    overall = sum(breakdown[name] * effective[name] for name in breakdown)
    required = breakdown.get("required_skills")
    return {"score": round(overall * 100), "eligible": required is None or required >= 0.70, "breakdown": breakdown, "effective_weights": effective}
