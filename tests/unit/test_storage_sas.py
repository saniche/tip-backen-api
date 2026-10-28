import base64
from urllib.parse import parse_qs, urlparse

from shared import storage


def test_real_sas_url_is_read_only_expiring_and_keeps_the_blob_path(monkeypatch):
    monkeypatch.setenv("AZURE_STORAGE_ACCOUNT_NAME", "tipaccount")
    monkeypatch.setenv("AZURE_STORAGE_ACCOUNT_KEY", base64.b64encode(b"k" * 32).decode())

    url = storage.generate_temporary_download_url("user-1/doc-1/jane-doe-cv.md", expires_minutes=15)

    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    assert parsed.netloc == "tipaccount.blob.core.windows.net"
    assert parsed.path == f"/{storage.CONTAINER_NAME}/user-1/doc-1/jane-doe-cv.md"  # slashes stay real slashes
    assert query["sp"] == ["r"]
    assert "se" in query and "sig" in query and "sv" in query
    assert "attachment" in query["rscd"][0] and "jane-doe-cv.md" in query["rscd"][0]


def test_without_credentials_a_clearly_fake_but_same_shaped_url_is_returned(monkeypatch):
    monkeypatch.delenv("AZURE_STORAGE_ACCOUNT_NAME", raising=False)
    monkeypatch.delenv("AZURE_STORAGE_ACCOUNT_KEY", raising=False)

    url = storage.generate_temporary_download_url("user-1/doc-1/cv.md")

    assert url.startswith("https://example.invalid/") and "sig=" in url
