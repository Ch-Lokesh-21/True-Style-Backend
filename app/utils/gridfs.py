# app/utils/gridfs.py
from __future__ import annotations
from typing import Tuple, Optional
from bson import ObjectId
from fastapi import UploadFile, HTTPException
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from urllib.parse import urlparse

from app.core.database import db
from app.core.config import settings


def build_file_url(file_id: ObjectId | str) -> str:
    """
    Build a public, downloadable URL for a stored GridFS file.

    Args:
        file_id: The ObjectId or string ID of the file in GridFS.

    Returns:
        str: A fully qualified API endpoint URL for downloading the file.
    """
    fid = str(file_id)
    return f"{settings.BACKEND_BASE_URL.rstrip('/')}{settings.API_V1_PREFIX}/files/{fid}"


def _bucket():
    """
    Create a GridFS bucket instance.

    Returns:
        AsyncIOMotorGridFSBucket: The active GridFS bucket tied to the app database.
    """
    return AsyncIOMotorGridFSBucket(db, bucket_name=settings.GRIDFS_BUCKET)


def _extract_file_id_from_url(url: Optional[str]) -> Optional[str]:
    """
    Extract a GridFS file_id from a full download URL.

    Works with URLs generated via build_file_url:
        {BACKEND_BASE_URL}{API_V1_PREFIX}/files/<id>

    Args:
        url (str | None): Full or relative URL.

    Returns:
        str | None: The extracted file_id if present, else None.
    """
    if not url:
        return None
    parsed = urlparse(url)
    path = parsed.path or ""
    parts = path.split("/files/", 1)
    if len(parts) != 2 or not parts[1]:
        return None
    return parts[1].split("/")[0]


async def _validate_upload(file: UploadFile) -> None:
    """
    Validate the content type of an uploaded file.

    Raises:
        HTTPException(415): If file type is not allowed.
    """
    allowed = {x.strip().lower() for x in settings.UPLOAD_ALLOWED_TYPES.split(",") if x.strip()}
    if file.content_type is None or file.content_type.lower() not in allowed:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported content type: {file.content_type}"
        )


async def upload_image(file: UploadFile) -> Tuple[str, str]:
    """
    Stream an uploaded file into GridFS.

    Args:
        file (UploadFile): The incoming file to store.

    Returns:
        Tuple[str, str]: (file_id, public_download_url)

    Raises:
        HTTPException(413): File exceeds max upload size.
        HTTPException(415): Unsupported file type.
        HTTPException(500): Any internal GridFS failure.
    """
    await _validate_upload(file)
    bucket = _bucket()
    filename = file.filename or "upload.bin"

    max_bytes = settings.UPLOAD_MAX_BYTES
    written = 0

    try:
        # NOTE: do not await the constructor
        grid_in = bucket.open_upload_stream(
            filename=filename,
            metadata={"contentType": file.content_type or "application/octet-stream"},
        )
        try:
            while True:
                chunk = await file.read(1024 * 64)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    await grid_in.abort()
                    raise HTTPException(status_code=413, detail="Uploaded file too large")
                await grid_in.write(chunk)
        finally:
            await grid_in.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {e}")

    file_id = grid_in._id
    return str(file_id), build_file_url(file_id)


async def delete_image(file_id: str) -> bool:
    """
    Delete a file from GridFS.

    Args:
        file_id (str): The string ID of the GridFS file.

    Returns:
        bool: True if deleted, False if invalid ID or file not found.
    """
    bucket = _bucket()
    try:
        oid = ObjectId(file_id)
    except Exception:
        return False

    try:
        await bucket.delete(oid)
        return True
    except Exception:
        return False


async def replace_image(old_file_id: Optional[str], new_file: UploadFile) -> Tuple[str, str]:
    """
    Replace an existing GridFS file with a new upload.

    Args:
        old_file_id (str | None): Current file's GridFS ID (if any).
        new_file (UploadFile): New uploaded file to store.

    Returns:
        Tuple[str, str]: (new_file_id, public_download_url)
    """
    new_id, new_url = await upload_image(new_file)
    if old_file_id:
        await delete_image(old_file_id)
    return new_id, new_url
