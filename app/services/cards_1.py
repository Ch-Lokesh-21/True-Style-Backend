from __future__ import annotations
from typing import List, Optional

from fastapi import HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.schemas.object_id import PyObjectId
from app.schemas.cards_1 import Cards1Create, Cards1Update, Cards1Out
from app.crud import cards_1 as crud
from app.utils.gridfs import upload_image, replace_image, delete_image, _extract_file_id_from_url


async def create_item_service(idx: int, title: str, image: UploadFile) -> Cards1Out:
    """
    Create a new Cards1 item. Streams image to GridFS and stores image_url.
    """
    try:
        _, url = await upload_image(image)
        payload = Cards1Create(idx=idx, title=title, image_url=url)
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "E11000" in msg and "idx" in msg:
            raise HTTPException(status_code=409, detail="Duplicate idx.")
        raise HTTPException(status_code=500, detail=f"Failed to create Cards1: {e}")


async def list_items_service(skip: int, limit: int, sort_by_idx: bool) -> List[Cards1Out]:
    try:
        return await crud.list_all(skip=skip, limit=limit, sort_by_idx=sort_by_idx)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list Cards1: {e}")


async def get_item_service(item_id: PyObjectId) -> Cards1Out:
    try:
        d = await crud.get_one(item_id)
        if not d:
            raise HTTPException(status_code=404, detail="Cards1 not found")
        return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Cards1: {e}")


async def update_item_service(
    item_id: PyObjectId,
    idx: Optional[int] = None,
    title: Optional[str] = None,
    image: UploadFile = None,  # optional in service
) -> Cards1Out:
    """
    Update fields; if image is provided, replace it in GridFS and update image_url.
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=404, detail="Cards1 not found")

        patch = Cards1Update()

        if image is not None:
            old_id = _extract_file_id_from_url(current.image_url)
            if old_id:
                _, new_url = await replace_image(old_id, image)
            else:
                # fallback: if old file id not parseable, just upload
                _, new_url = await upload_image(image)
            patch.image_url = new_url  # type: ignore[attr-defined]

        if idx is not None:
            patch.idx = idx
        if title is not None:
            patch.title = title

        if not any(v is not None for v in patch.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")

        updated = await crud.update_one(item_id, patch)
        if not updated:
            # could be not found or duplicate idx in unique index
            raise HTTPException(status_code=409, detail="Update failed (possibly duplicate idx).")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "E11000" in msg and "idx" in msg:
            raise HTTPException(status_code=409, detail="Duplicate idx.")
        raise HTTPException(status_code=500, detail=f"Failed to update Cards1: {e}")


async def delete_item_service(item_id: PyObjectId):
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=404, detail="Cards1 not found")

        file_id = _extract_file_id_from_url(current.image_url)
        if file_id:
            await delete_image(file_id)

        ok = await crud.delete_one(item_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Cards1 not found")
        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete Cards1: {e}")