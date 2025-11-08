from __future__ import annotations
from bson import ObjectId
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from app.utils.gridfs import _bucket
from app.schemas.object_id import PyObjectId
async def file_download_service(file_id:PyObjectId):
    try:
        oid = ObjectId(file_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file id")
    bucket = _bucket()
    try:
        grid_out = await bucket.open_download_stream(oid)
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")

    media_type = grid_out.metadata.get("contentType") if grid_out.metadata else "application/octet-stream"

    async def iterfile():
        while True:
            chunk = await grid_out.readchunk()
            if not chunk:
                break
            yield chunk
    return StreamingResponse(iterfile(), media_type=media_type)