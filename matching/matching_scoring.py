from matching.llm_matching import ItemMatching, MatchingCriteria

WEIGHTS = {"requirements": 0.75, "desirables": 0.25}


def _judgment(item: ItemMatching) -> str:
    if item.judgment not in {"Yes", "No"}:
        raise ValueError("Matching judgments must be exactly Yes or No.")
    return item.judgment


def _category_score(items: list[ItemMatching]) -> float | None:
    if not items:
        return None
    return sum(_judgment(item) == "Yes" for item in items) / len(items)


def score_match(
    requirements: list[ItemMatching],
    desirables: list[ItemMatching],
    criteria: MatchingCriteria,
) -> dict:
    category_scores = {
        "requirements": _category_score(requirements),
        "desirables": _category_score(desirables),
    }
    available = {name: score for name, score in category_scores.items() if score is not None}
    if not available:
        return {
            "score": None,
            "eligible": False,
            "scoring_status": "unscorable",
            "breakdown": {},
            "effective_weights": {},
        }

    total_weight = sum(WEIGHTS[name] for name in available)
    effective_weights = {name: WEIGHTS[name] / total_weight for name in available}
    overall = sum(available[name] * effective_weights[name] for name in available)

    if len(requirements) == len(criteria.requirements):
        count = len(criteria.required_qualifications)
        qualification_judgments = requirements[:count]
        skill_judgments = requirements[count:]
    else:
        # Criteria were split or reworded, so positions no longer line up; match by text.
        qualification_texts = {text.casefold() for text in criteria.required_qualifications}
        qualification_judgments = [
            item for item in requirements if item.criterion.casefold() in qualification_texts
        ]
        skill_judgments = [
            item for item in requirements if item.criterion.casefold() not in qualification_texts
        ]
    qualifications_satisfied = all(_judgment(item) == "Yes" for item in qualification_judgments)
    skill_score = _category_score(skill_judgments)
    skills_satisfied = skill_score is None or skill_score >= 0.70

    return {
        "score": round(overall * 100),
        "eligible": qualifications_satisfied and skills_satisfied,
        "scoring_status": "scored",
        "breakdown": available,
        "effective_weights": effective_weights,
    }
