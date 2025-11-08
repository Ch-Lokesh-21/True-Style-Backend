# app/api/routes/files.py
from __future__ import annotations
from fastapi import APIRouter
from app.services.files import file_download_service
from app.schemas.object_id import PyObjectId
router = APIRouter()



@router.get("/{file_id}")
async def download_file(file_id: PyObjectId):
    return await file_download_service(file_id)
