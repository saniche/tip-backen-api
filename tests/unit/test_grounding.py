from shared.grounding import source_vocabulary, unsupported_facts, unsupported_terms


def test_natural_phrasing_with_function_words_and_inflections_is_accepted():
    # "with" used to be rejected because it was not in the cited evidence
    assert unsupported_terms("Built REST APIs with Python", ["Build REST APIs in Python"]) == set()
    assert unsupported_terms("Building APIs", ["Build API"]) == set()
    assert unsupported_terms("Python avec FastAPI", ["Python", "FastAPI"]) == set()


def test_numbers_must_be_backed_by_the_evidence():
    assert unsupported_terms("Reduced costs by 40%", ["Reduced costs"]) == {"40"}
    assert unsupported_terms("Reduced costs by 40%", ["Reduced costs by 40%"]) == set()


def test_title_and_leadership_inflation_is_still_rejected_even_for_short_words():
    assert unsupported_terms("Led platform migration", ["Platform migration"]) == {"Led"}
    assert unsupported_terms("Senior engineer", ["Engineer"]) == {"Senior"}
    assert unsupported_terms("Led platform migration", ["Led platform migration"]) == set()


def test_words_that_are_not_in_the_evidence_are_still_rejected():
    assert unsupported_terms("Python engineer architect", ["Python engineer"]) == {"architect"}


def test_fact_check_allows_free_prose_but_flags_invented_facts():
    vocabulary = source_vocabulary(["Python engineer at Acme Corp", "Built APIs"])
    assert unsupported_facts("I am excited to contribute to your mission.", vocabulary) == set()
    assert unsupported_facts("I worked at Acme Corp on Python APIs.", vocabulary) == set()
    flagged = unsupported_facts("I led the Google team in 2019. A senior engineer.", vocabulary)
    assert {"Google", "2019", "led", "senior"} <= flagged
