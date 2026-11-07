"""
Azure Blob Storage helper — the ONLY place file bytes live outside the DB. Everything structured
(users, jobs, profiles, matches) stays in PostgreSQL; only the generated CV files go here, so the
API stays stateless across instances/restarts.
"""

import hashlib
import hmac
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import BlobSasPermissions, BlobServiceClient, ContentSettings, generate_blob_sas

CONTAINER_NAME = os.environ.get("CV_BLOB_CONTAINER", "tailored-cvs")
_connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "UseDevelopmentStorage=true")

if _connection_string == "UseDevelopmentStorage=true":
    _blob_service_client = None
else:
    _blob_service_client = BlobServiceClient.from_connection_string(_connection_string)


def _use_local_blob_store() -> bool:
    return _connection_string == "UseDevelopmentStorage=true"


def _local_blob_path(blob_path: str) -> Path:
    root = Path(os.environ.get("LOCAL_BLOB_DIRECTORY", ".local-blobs")).resolve()
    path = (root / blob_path).resolve()
    if path == root or not path.is_relative_to(root):
        raise ValueError("Invalid local blob path")
    return path


def _upload_local_blob(blob_path: str, content: str) -> str:
    path = _local_blob_path(blob_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as temp:
            temp_path = Path(temp.name)
            temp.write(content)
        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
    return blob_path


def _download_local_blob(blob_path: str) -> str:
    return _local_blob_path(blob_path).read_text(encoding="utf-8")


def _get_container_client():
    if _use_local_blob_store():
        return None
    container_client = _blob_service_client.get_container_client(CONTAINER_NAME)
    if not container_client.exists():
        try:
            container_client.create_container()
        except ResourceExistsError:
            pass
    return container_client


def upload_markdown(blob_path: str, content: str) -> str:
    """Uploads markdown content to blob storage. Returns the blob_path (used as the DB key)."""
    container_client = _get_container_client()
    if container_client is None:
        return _upload_local_blob(blob_path, content)
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
    if container_client is None:
        return _download_local_blob(blob_path)
    blob_client = container_client.get_blob_client(blob_path)
    return blob_client.download_blob().readall().decode("utf-8")


def delete_blob(blob_path: str) -> None:
    container_client = _get_container_client()
    if container_client is None:
        _local_blob_path(blob_path).unlink(missing_ok=True)
        return
    try:
        container_client.delete_blob(blob_path)
    except ResourceNotFoundError:
        pass


def build_blob_path(user_id: str, tailored_cv_id: str, filename: str) -> str:
    return f"{user_id}/{tailored_cv_id}/{filename}"


def generate_temporary_download_url(blob_path: str, expires_minutes: int = 60) -> str:
    """Read-only, expiring download link.

    With AZURE_STORAGE_ACCOUNT_NAME/KEY configured this is a real Azure Blob SAS URL (service SAS,
    read permission, forced attachment filename). Without credentials (local/dev) it returns a
    clearly fake, never-resolvable URL so the API shape stays the same.
    """
    account_name = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
    account_key = os.environ.get("AZURE_STORAGE_ACCOUNT_KEY")
    expires = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)

    if not account_name or not account_key:
        expiry = int(expires.timestamp())
        signed = hmac.new(b"dev-key", f"{blob_path}|{expiry}".encode("utf-8"), hashlib.sha256).hexdigest()
        return f"https://example.invalid/download/{quote(blob_path, safe='')}?expires={expiry}&sig={signed}"

    filename = blob_path.rsplit("/", 1)[-1]
    token = generate_blob_sas(
        account_name=account_name,
        container_name=CONTAINER_NAME,
        blob_name=blob_path,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=expires,
        content_disposition=f'attachment; filename="{filename}"',
        content_type="text/markdown; charset=utf-8",
    )
    return f"https://{account_name}.blob.core.windows.net/{CONTAINER_NAME}/{quote(blob_path, safe='/')}?{token}"
