from matching_scoring import score_match


def test_score_redistributes_missing_groups_and_calculates_eligibility():
    result = score_match({"required_skills": [{"result": "Yes"}], "technical_stack": [{"result": "Partial"}]})
    assert result["score"] == 94
    assert result["eligible"] is True
    assert round(sum(result["effective_weights"].values()), 5) == 1
