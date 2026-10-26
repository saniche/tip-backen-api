from dataclasses import dataclass

from matching.llm_matching import JobData, LlmMatchOutput, matching_criteria
from matching.matching_scoring import score_match


@dataclass
class MatchResult:
    score: int | None
    eligible: bool
    scoring_status: str
    breakdown: dict | None = None
    effective_weights: dict | None = None


def build_match_result(llm_output: LlmMatchOutput, job: JobData) -> MatchResult:
    scored = score_match(llm_output.requirements, llm_output.desirables, matching_criteria(job))
    return MatchResult(
        score=scored["score"],
        eligible=scored["eligible"],
        scoring_status=scored["scoring_status"],
        breakdown=scored["breakdown"],
        effective_weights=scored["effective_weights"],
    )
