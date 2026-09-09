"""
Azure Blob Storage helper — the ONLY place file bytes live outside the DB. Everything structured
(users, jobs, profiles, matches) stays in PostgreSQL; only the generated CV files go here, so the
API stays stateless across instances/restarts.
"""

import os
from azure.storage.blob import BlobServiceClient, ContentSettings

CONTAINER_NAME = os.environ.get("CV_BLOB_CONTAINER", "tailored-cvs")
_connection_string = os.environ["AZURE_STORAGE_CONNECTION_STRING"]

_blob_service_client = BlobServiceClient.from_connection_string(_connection_string)


def _get_container_client():
    container_client = _blob_service_client.get_container_client(CONTAINER_NAME)
    if not container_client.exists():
        container_client.create_container()
    return container_client


def upload_markdown(blob_path: str, content: str) -> str:
    """Uploads markdown content to blob storage. Returns the blob_path (used as the DB key)."""
    container_client = _get_container_client()
    container_client.upload_blob(
        name=blob_path,
        data=content.encode("utf-8"),
        overwrite=True,
        content_settings=ContentSettings(content_type="text/markdown"),
    )
    return blob_path


def download_markdown(blob_path: str) -> str:
    """Downloads and returns the markdown content stored at blob_path."""
    container_client = _get_container_client()
    blob_client = container_client.get_blob_client(blob_path)
    return blob_client.download_blob().readall().decode("utf-8")


def build_blob_path(user_id: str, tailored_cv_id: str, filename: str) -> str:
    return f"{user_id}/{tailored_cv_id}/{filename}"
