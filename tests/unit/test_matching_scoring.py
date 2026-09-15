from matching.matching_scoring import score_match


def test_score_redistributes_missing_groups_and_calculates_eligibility():
    result = score_match({"required_skills": [{"result": "Yes"}], "technical_stack": [{"result": "Partial"}]})
    assert result["score"] == 94
    assert result["eligible"] is True
    assert round(sum(result["effective_weights"].values()), 5) == 1


def test_unmet_required_qualification_blocks_eligibility_even_with_perfect_required_skills():
    # required_skills alone clears the 70% bar, but one required qualification is a hard "No" —
    # eligibility must be strict (no partial credit) on required_qualifications regardless of score.
    result = score_match(
        {
            "required_qualifications": [{"result": "Yes"}, {"result": "No"}],
            "required_skills": [{"result": "Yes"}, {"result": "Yes"}],
        }
    )
    assert result["eligible"] is False


def test_partial_required_qualification_also_blocks_eligibility():
    # "strict, no partial credit" means Partial doesn't count as matched either.
    result = score_match(
        {
            "required_qualifications": [{"result": "Partial"}],
            "required_skills": [{"result": "Yes"}],
        }
    )
    assert result["eligible"] is False


def test_all_required_qualifications_matched_allows_eligibility():
    result = score_match(
        {
            "required_qualifications": [{"result": "Yes"}, {"result": "Yes"}],
            "required_skills": [{"result": "Yes"}],
        }
    )
    assert result["eligible"] is True
