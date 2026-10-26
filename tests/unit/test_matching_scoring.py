from matching.job_matching import build_match_result
from matching.llm_matching import ItemMatching, JobData, LlmMatchOutput, MatchAnalysis, matching_criteria
from matching.matching_scoring import score_match


def assessment(criterion: str, judgment: str) -> ItemMatching:
    return ItemMatching(criterion=criterion, judgment=judgment, evidence=f"Evidence about {criterion}.")


def result(requirements: list[str], desirables: list[str]) -> LlmMatchOutput:
    return LlmMatchOutput(
        requirements=[assessment(f"req-{index}", judgment) for index, judgment in enumerate(requirements)],
        desirables=[assessment(f"des-{index}", judgment) for index, judgment in enumerate(desirables)],
        notes="Criteria evaluated.",
        analysis=MatchAnalysis(
            eligibility="Evidence is assessed against mandatory criteria.",
            matching="The profile was compared with each criterion.",
            chance_of_success="Hiring remains uncertain.",
        ),
    )


def score(requirements: list[str], desirables: list[str]) -> dict:
    job = JobData(
        required={"qualifications": [], "skills": [f"req-{index}" for index in range(len(requirements))]},
        desirable={"qualifications": [], "skills": [f"des-{index}" for index in range(len(desirables))]},
    )
    matching_output = result(requirements, desirables)
    return score_match(matching_output.requirements, matching_output.desirables, matching_criteria(job))


def test_all_yes_and_all_no_scores():
    assert score(["Yes", "Yes"], ["Yes"])["score"] == 100
    assert score(["No", "No"], ["No"])["score"] == 0


def test_mixed_judgments_use_75_percent_and_25_percent_weights():
    result_value = score(["Yes", "Yes"], ["No"])

    assert result_value["score"] == 75
    assert result_value["effective_weights"] == {"requirements": 0.75, "desirables": 0.25}
    assert result_value["breakdown"] == {"requirements": 1.0, "desirables": 0.0}


def test_existing_rounding_convention_is_preserved():
    assert score(["Yes"], ["No"])["score"] == 75
    assert score(["Yes", "No"], ["No"])["score"] == 38


def test_only_non_empty_category_receives_full_weight():
    desirables_only = score([], ["Yes", "No"])
    requirements_only = score(["Yes", "No"], [])

    assert desirables_only["score"] == 50
    assert desirables_only["effective_weights"] == {"desirables": 1.0}
    assert requirements_only["score"] == 50
    assert requirements_only["effective_weights"] == {"requirements": 1.0}


def test_empty_categories_return_none_and_are_unscorable():
    result_value = score([], [])

    assert result_value["score"] is None
    assert result_value["scoring_status"] == "unscorable"
    assert result_value["eligible"] is False
    assert result_value["breakdown"] == {}


def test_eligibility_remains_separate_and_preserves_existing_rules():
    qualifying_job = JobData(
        required={"qualifications": ["Degree"], "skills": ["Python", "SQL"]},
        desirable=[],
    )
    qualified = LlmMatchOutput(
        requirements=[
            assessment("Degree", "Yes"),
            assessment("Python", "Yes"),
            assessment("SQL", "Yes"),
        ],
        desirables=[],
        notes="Assessed.",
        analysis=MatchAnalysis(
            eligibility="Assessment.",
            matching="Assessment.",
            chance_of_success="Assessment.",
        ),
    )
    unqualified = LlmMatchOutput(
        requirements=[
            assessment("Degree", "No"),
            assessment("Python", "Yes"),
            assessment("SQL", "Yes"),
        ],
        desirables=[],
        notes="Assessed.",
        analysis=qualified.analysis,
    )

    assert build_match_result(qualified, qualifying_job).eligible is True
    assert build_match_result(unqualified, qualifying_job).eligible is False


def test_required_skills_keep_existing_seventy_percent_eligibility_threshold():
    skills = [f"Skill {index}" for index in range(10)]
    job = JobData(required={"qualifications": [], "skills": skills}, desirable=[])
    seven_yes = LlmMatchOutput(
        requirements=[assessment(skill, "Yes" if index < 7 else "No") for index, skill in enumerate(skills)],
        desirables=[],
        notes="Assessed.",
        analysis=MatchAnalysis(
            eligibility="Assessment.",
            matching="Assessment.",
            chance_of_success="Assessment.",
        ),
    )
    six_yes = seven_yes.model_copy(
        update={
            "requirements": [
                assessment(skill, "Yes" if index < 6 else "No") for index, skill in enumerate(skills)
            ]
        }
    )

    assert build_match_result(seven_yes, job).eligible is True
    assert build_match_result(six_yes, job).eligible is False


def test_context_and_analysis_do_not_contribute_to_scoring():
    first_job = JobData(required=["Python"], desirable=["FastAPI"], technical_stack=["Python"])
    second_job = JobData(
        required=["Python"],
        desirable=["FastAPI"],
        technical_stack=["Rust", "Kubernetes"],
        key_responsibilities=["Completely different responsibilities"],
    )
    first = result(["Yes"], ["No"])
    second = first.model_copy(
        update={
            "analysis": MatchAnalysis(
                eligibility="No conditions verified.",
                matching="Different narrative.",
                chance_of_success="Very uncertain.",
            )
        }
    )

    assert build_match_result(first, first_job).score == build_match_result(second, second_job).score


def test_invalid_judgments_never_count_as_no_or_other_score():
    invalid = ItemMatching.model_construct(criterion="Python", judgment="Partial", evidence="Evidence.")
    try:
        score_match([invalid], [], matching_criteria(JobData(required=["Python"])))
    except ValueError as error:
        assert "exactly Yes or No" in str(error)
    else:
        raise AssertionError("An invalid judgment must not contribute to a score.")
