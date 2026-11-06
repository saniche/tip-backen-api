import os
import subprocess
import sys

import pytest

from shared import storage


def test_local_blob_is_available_to_another_process():
    storage.upload_markdown("user/record/document.md", "shared content")

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from shared.storage import download_markdown; print(download_markdown('user/record/document.md'))",
        ],
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == "shared content"
    storage.delete_blob("user/record/document.md")
    with pytest.raises(FileNotFoundError):
        storage.download_markdown("user/record/document.md")


def test_local_blob_rejects_paths_outside_storage():
    with pytest.raises(ValueError):
        storage.upload_markdown("../outside.md", "content")


def test_azure_errors_do_not_fall_back_to_local_storage(monkeypatch):
    class BrokenContainer:
        def exists(self):
            raise RuntimeError("Storage unavailable")

    class BrokenService:
        def get_container_client(self, name):
            return BrokenContainer()

    monkeypatch.setattr(storage, "_connection_string", "azure")
    monkeypatch.setattr(storage, "_blob_service_client", BrokenService())

    with pytest.raises(RuntimeError, match="Storage unavailable"):
        storage.upload_markdown("user/record/document.md", "content")
