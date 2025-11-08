# app/utils/gridfs.py
from __future__ import annotations
from typing import Tuple, Optional
from bson import ObjectId
from fastapi import UploadFile, HTTPException
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from app.core.database import db
from app.core.config import settings
from urllib.parse import urlparse
def build_file_url(file_id: ObjectId | str) -> str:
    fid = str(file_id)
    return f"{settings.BACKEND_BASE_URL.rstrip('/')}{settings.API_V1_PREFIX}/files/{fid}"

def _bucket():
    return AsyncIOMotorGridFSBucket(db, bucket_name=settings.GRIDFS_BUCKET)

def _extract_file_id_from_url(url: Optional[str]) -> Optional[str]:
    """
    Works with URLs built by build_file_url():
      {BACKEND_BASE_URL}{API_V1_PREFIX}/files/<id>
    Handles absolute/relative forms.
    """
    if not url:
        return None
    parsed = urlparse(url)
    path = parsed.path or ""
    parts = path.split("/files/", 1)
    if len(parts) != 2 or not parts[1]:
        return None
    return parts[1].split("/")[0]

def _bucket():
    return AsyncIOMotorGridFSBucket(db, bucket_name=settings.GRIDFS_BUCKET)

async def _validate_upload(file: UploadFile) -> None:
    allowed = {x.strip().lower() for x in settings.UPLOAD_ALLOWED_TYPES.split(",") if x.strip()}
    if file.content_type is None or file.content_type.lower() not in allowed:
        raise HTTPException(status_code=415, detail=f"Unsupported content type: {file.content_type}")

async def upload_image(file: UploadFile) -> Tuple[str, str]:
    """
    Streams an UploadFile into GridFS.
    Returns: (file_id_str, public_url)
    """
    await _validate_upload(file)
    bucket = _bucket()
    filename = file.filename or "upload.bin"

    max_bytes = settings.UPLOAD_MAX_BYTES
    written = 0

    try:
        # NOTE: DO NOT await this line
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
                    # abort is async
                    await grid_in.abort()
                    raise HTTPException(status_code=413, detail="Uploaded file too large")
                # write is async
                await grid_in.write(chunk)
        finally:
            # close is async
            await grid_in.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {e}")

    file_id = grid_in._id  # ObjectId
    return str(file_id), build_file_url(file_id)

async def delete_image(file_id: str) -> bool:
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
    new_id, new_url = await upload_image(new_file)
    if old_file_id:
        await delete_image(old_file_id)
    return new_id, new_url