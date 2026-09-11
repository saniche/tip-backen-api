import pytest
from fastapi import HTTPException

from authorization import require_owner_or_admin
from storage import generate_temporary_download_url


class DummyUser:
    def __init__(self, user_id: str, role: str = "user"):
        self.id = user_id
        self.role = role


def test_generate_temporary_download_url_includes_signed_blob_url():
    url = generate_temporary_download_url("user-1/report.md", expires_minutes=15)
    assert url.startswith("https://")
    assert "sig=" in url.lower()
    assert "user-1%2Freport.md" in url or "user-1/report.md" in url


def test_require_owner_or_admin_rejects_non_owners():
    other = DummyUser("other-1")
    with pytest.raises(HTTPException) as exc:
        require_owner_or_admin(owner_id="owner-1", current_user=other)
    assert exc.value.status_code == 403
