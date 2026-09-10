from profile_service import consolidate_profile_fragments


def test_consolidate_profile_fragments_uses_user_precedence_over_inferred_values():
    fragments = [
        {
            "data": {
                "name": "Alice Example",
                "summary": "Senior software engineer with Python experience.",
                "skills": ["Python", "SQL"],
                "languages": ["English"],
            },
            "evidence_type": "extracted",
        },
        {
            "data": {
                "summary": "This was inferred and should be replaced.",
                "skills": ["Python", "FastAPI"],
            },
            "evidence_type": "inferred",
        },
        {
            "data": {
                "summary": "Lead software engineer.",
                "skills": ["Python", "PostgreSQL"],
                "languages": ["English", "Spanish"],
            },
            "evidence_type": "user_edited",
        },
    ]

    result = consolidate_profile_fragments(fragments)

    assert result["name"] == "Alice Example"
    assert result["summary"] == "Lead software engineer."
    assert result["skills"] == ["Python", "PostgreSQL"]
    assert result["languages"] == ["English", "Spanish"]
