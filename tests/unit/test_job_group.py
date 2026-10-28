from types import SimpleNamespace

import pytest

from cv.job_group import merge_jobs


def _job(title, company, required, tools, responsibilities=(), summary="s"):
    return SimpleNamespace(
        title=title,
        company=company,
        location=None,
        summary=summary,
        required=required,
        desirable={},
        tools_and_technologies=list(tools),
        key_responsibilities=list(responsibilities),
    )


def test_single_job_group_is_passed_through_unchanged():
    job = _job("Engineer", "Acme", {"qualifications": ["BSc"], "skills": ["Python"]}, ["Python"], summary="About")

    merged = merge_jobs([job])

    assert merged.data.title == "Engineer"
    assert merged.data.required == {"qualifications": ["BSc"], "skills": ["Python"]}
    assert merged.data.summary == "About"
    assert merged.company == "Acme"


def test_group_uses_every_job_not_only_the_first_and_ranks_shared_items_first():
    first = _job("Python Engineer", "Acme", {"qualifications": ["BSc"], "skills": ["Python", "SQL"]}, ["Python"])
    second = _job("Data Engineer", "Acme", {"qualifications": [], "skills": ["spark", "python"]}, ["Spark", "python"])

    merged = merge_jobs([first, second])

    assert merged.data.title == "Python Engineer / Data Engineer"
    assert merged.data.required["skills"][0] == "Python"  # asked by both jobs, case-insensitive
    assert set(merged.data.required["skills"]) == {"Python", "SQL", "spark"}
    assert merged.data.required["qualifications"] == ["BSc"]
    assert merged.data.tools_and_technologies[0] == "Python"
    assert "Spark" in merged.data.tools_and_technologies
    assert merged.data.summary is None
    assert merged.company == "Acme"


def test_group_company_is_unknown_when_postings_differ_and_titles_are_deduplicated():
    jobs = [_job("Engineer", "Acme", [], []), _job("Engineer", "Globex", [], [])]

    merged = merge_jobs(jobs)

    assert merged.data.title == "Engineer"
    assert merged.company is None


def test_list_shaped_requirements_are_merged_too():
    merged = merge_jobs([_job("A", "X", ["Python"], []), _job("B", "X", ["Python", "Go"], [])])

    assert merged.data.required == ["Python", "Go"]


def test_empty_group_is_rejected():
    with pytest.raises(ValueError):
        merge_jobs([])
