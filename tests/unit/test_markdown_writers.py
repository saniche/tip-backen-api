from datetime import date
from profile.profile_builder import UserProfile

from cover_letter.cover_letter_tailoring import TailoredCoverLetter
from cover_letter.cover_letter_writer import render_cover_letter_markdown, suggest_cover_letter_filename
from cv.cv_tailoring import TailoredCv
from cv.markdown_writer import render_tailored_cv_markdown, suggest_filename

PROFILE = UserProfile(
    Name="Jane Doe",
    Location="Ottawa, ON",
    Phone="+1 (613) 555-0100",
    Email="jane@example.com",
    LinkedIn="linkedin.com/in/jane",
)


def test_cv_has_deterministic_header_and_omits_empty_sections():
    cv = TailoredCv(
        target_role="Python Engineer", summary="Builds APIs.", experience=["Built APIs"], skills=["Python", "SQL"]
    )

    markdown = render_tailored_cv_markdown(cv, PROFILE)

    lines = markdown.splitlines()
    assert lines[0] == "# Jane Doe"
    assert "Ottawa, ON" in markdown
    assert "[+1 (613) 555-0100](tel:+16135550100)" in markdown
    assert "<jane@example.com>" in markdown
    assert "[linkedin.com/in/jane](https://linkedin.com/in/jane)" in markdown
    assert "## Python Engineer" in markdown
    assert "## Experience\n- Built APIs" in markdown
    assert "## Skills\nPython, SQL" in markdown
    assert "## Education" not in markdown and "## Certifications" not in markdown


def test_cv_without_profile_keeps_a_neutral_title():
    assert render_tailored_cv_markdown(TailoredCv(target_role="Engineer", summary="S")).startswith("# Tailored CV")


def test_filenames_are_blob_safe_even_for_group_titles():
    cv = TailoredCv(target_role="Python Engineer / Data Engineer")

    assert suggest_filename(cv, PROFILE) == "jane-doe-python-engineer-data-engineer-cv.md"
    assert "/" not in suggest_filename(cv)
    assert suggest_filename(TailoredCv()) == "tailored-cv.md"


def test_cover_letter_layout_uses_code_for_facts_and_llm_text_for_prose():
    letter = TailoredCoverLetter(
        greeting="Dear Hiring Manager,", paragraphs=["First.", "Second."], closing="Sincerely,"
    )

    markdown = render_cover_letter_markdown(letter, PROFILE, "Python Engineer", "Acme", today=date(2026, 10, 27))

    assert markdown.startswith("# Jane Doe")
    assert "2026-10-27" in markdown
    assert "Hiring Team, Acme" in markdown and "**Re: Python Engineer**" in markdown
    assert markdown.index("Dear Hiring Manager,") < markdown.index("First.") < markdown.index("Second.")
    assert markdown.rstrip().splitlines()[-2:] == ["Sincerely,", "Jane Doe"]
    assert suggest_cover_letter_filename(PROFILE, "Python Engineer", "Acme") == "jane-doe-acme-cover-letter.md"
    assert "Hiring Team\n" in render_cover_letter_markdown(letter, PROFILE, "", None)
