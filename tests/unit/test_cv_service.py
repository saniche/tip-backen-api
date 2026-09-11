import pytest

from cv_service import validate_cv_selection


def test_cv_selection_rejects_mixed_owners_and_empty_selection():
    with pytest.raises(ValueError, match="At least one"):
        validate_cv_selection([], "per_job")
    with pytest.raises(ValueError, match="same owner"):
        validate_cv_selection([{"user_id": "one"}, {"user_id": "two"}], "group_all")


def test_cv_selection_accepts_supported_modes():
    assert validate_cv_selection([{"user_id": "one"}], "per_job") is None
    assert validate_cv_selection([{"user_id": "one"}], "group_all") is None