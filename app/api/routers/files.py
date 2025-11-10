"""
File Download Routes

Exposes a public endpoint that allows downloading stored files (e.g., images, PDFs)
from GridFS or other storage backends using a valid ObjectId.
"""

from __future__ import annotations
from fastapi import APIRouter
from app.services.files import file_download_service
from app.schemas.object_id import PyObjectId

router = APIRouter()


@router.get("/{file_id}")
async def download_file(file_id: PyObjectId):
    """
    Download a stored file by its GridFS/ObjectId identifier.

    Args:
        file_id (PyObjectId): The unique ObjectId of the file to retrieve.

    Returns:
        StreamingResponse: The raw file stream plus correct headers
        (content-type and content-disposition) for download.

    Raises:
        HTTPException 404: If no file exists for the provided ObjectId.
        HTTPException 500: If file retrieval fails unexpectedly.
    """
    return await file_download_service(file_id)