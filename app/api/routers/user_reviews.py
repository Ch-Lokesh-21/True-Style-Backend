from __future__ import annotations
from typing import List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.api.deps import user_required, admin_required
from app.schemas.object_id import PyObjectId
from app.schemas.user_reviews import UserReviewsCreate, UserReviewsUpdate, UserReviewsOut
from app.crud import user_reviews as crud
from app.utils.gridfs import upload_image, replace_image, delete_image

router = APIRouter()

def _extract_file_id_from_url(url: Optional[str]) -> Optional[str]:
    """Extract GridFS file_id from URLs like .../files/<id>[?...]."""
    if not url:
        return None
    p = urlparse(url)
    path = p.path or ""
    parts = path.split("/files/", 1)
    if len(parts) != 2 or not parts[1]:
        return None
    return parts[1].split("/")[0]

@router.post(
    "/",
    response_model=UserReviewsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(admin_required)],
)
async def create_item(
    product_id: str = Form(...),
    user_id: str = Form(...),
    review_status_id: int = Form(...),
    review: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),  # optional file
    image_url: Optional[str] = Form(None),     # or direct URL
):
    """
    Create user review. If an image file is provided, store in GridFS and set image_url.
    """
    try:
        final_url = image_url
        if image is not None:
            _, final_url = await upload_image(image)

        payload = UserReviewsCreate(
            product_id=product_id,
            user_id=user_id,
            review_status_id=review_status_id,
            image_url=final_url,
            review=review,
        )
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create UserReview: {e}")

@router.get("/", response_model=List[UserReviewsOut], dependencies=[Depends(user_required)])
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    try:
        return await crud.list_all(skip=skip, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list UserReviews: {e}")

@router.get("/{item_id}", response_model=UserReviewsOut, dependencies=[Depends(user_required)])
async def get_item(item_id: PyObjectId):
    try:
        d = await crud.get_one(item_id)
        if not d:
            raise HTTPException(404, "UserReview not found")
        return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get UserReview: {e}")

@router.put("/{item_id}", response_model=UserReviewsOut, dependencies=[Depends(admin_required)])
async def update_item(
    item_id: PyObjectId,
    product_id: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
    review_status_id: Optional[int] = Form(None),
    review: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),  # optional new file
    image_url: Optional[str] = Form(None),     # or direct URL
):
    """
    Update user review. If a new image file is provided, replace the old GridFS file and update image_url.
    If only image_url is provided, we update the string without touching GridFS.
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(404, "UserReview not found")

        patch = UserReviewsUpdate()

        if image is not None:
            old_id = _extract_file_id_from_url(current.image_url)
            _, new_url = await replace_image(old_id, image)
            patch.image_url = new_url
        elif image_url is not None:
            patch.image_url = image_url

        if product_id is not None:
            patch.product_id = product_id
        if user_id is not None:
            patch.user_id = user_id
        if review_status_id is not None:
            patch.review_status_id = review_status_id
        if review is not None:
            patch.review = review

        if not any(v is not None for v in patch.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")

        updated = await crud.update_one(item_id, patch)
        if not updated:
            raise HTTPException(status_code=409, detail="Update failed")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update UserReview: {e}")

@router.delete("/{item_id}", dependencies=[Depends(admin_required)])
async def delete_item(item_id: PyObjectId):
    """
    Delete the review and try to clean up GridFS image if the stored URL points to /files/<id>.
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(404, "UserReview not found")

        file_id = _extract_file_id_from_url(current.image_url)
        if file_id:
            await delete_image(file_id)

        ok = await crud.delete_one(item_id)
        if not ok:
            raise HTTPException(404, "UserReview not found")
        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete UserReview: {e}")