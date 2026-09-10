from pipeline.job_matching import build_match_result
from pipeline.llm_matching import LlmMatchOutput


def test_build_match_result_scores_and_marks_eligible():
    output = LlmMatchOutput(
        required_qualifications=[{"result": "Yes", "value": "Bachelor's degree"}],
        required_skills=[{"result": "Yes", "value": "Python"}, {"result": "Partial", "value": "SQL"}],
        desirable_skills=[{"result": "Yes", "value": "FastAPI"}],
        technical_stack=[{"result": "Partial", "value": "PostgreSQL"}],
    )

    result = build_match_result(output)

    assert result.score >= 0
    assert result.eligible is True
    assert result.scoring_status == "scored"
    assert "required_skills" in result.breakdown
