from __future__ import annotations
from bson import ObjectId
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from app.utils.gridfs import _bucket
from app.schemas.object_id import PyObjectId


async def file_download_service(file_id: PyObjectId):
    """
    Stream a file stored in MongoDB GridFS back to the client.

    Args:
        file_id (PyObjectId): GridFS file identifier.

    Returns:
        StreamingResponse: An async streaming response that streams file chunks.

    Raises:
        HTTPException 400: If file_id is not a valid ObjectId.
        HTTPException 404: If file does not exist in GridFS.
    """
    try:
        oid = ObjectId(file_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file id")

    bucket = _bucket()

    # Try opening the download stream; if missing, return 404
    try:
        grid_out = await bucket.open_download_stream(oid)
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")

    # Detect MIME type if stored in metadata
    media_type = grid_out.metadata.get("contentType") if grid_out.metadata else "application/octet-stream"

    async def iterfile():
        """Chunked file reader to avoid loading entire file in memory."""
        while True:
            chunk = await grid_out.readchunk()
            if not chunk:
                break
            yield chunk

    return StreamingResponse(iterfile(), media_type=media_type)