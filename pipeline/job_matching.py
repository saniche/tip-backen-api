from dataclasses import dataclass

from matching_scoring import score_match
from pipeline.llm_matching import LlmMatchOutput


@dataclass
class MatchResult:
    score: int
    eligible: bool
    scoring_status: str
    breakdown: dict | None = None
    effective_weights: dict | None = None


def build_match_result(llm_output: LlmMatchOutput) -> MatchResult:
    groups = {
        "required_qualifications": llm_output.required_qualifications,
        "required_skills": llm_output.required_skills,
        "desirable_qualifications": llm_output.desirable_qualifications,
        "desirable_skills": llm_output.desirable_skills,
        "technical_stack": llm_output.technical_stack,
    }

    scored = score_match(groups)
    if not any(items for items in groups.values()):
        scoring_status = "unscorable"
    else:
        scoring_status = "scored"

    return MatchResult(
        score=scored["score"],
        eligible=scored["eligible"],
        scoring_status=scoring_status,
        breakdown=scored.get("breakdown"),
        effective_weights=scored.get("effective_weights"),
    )
