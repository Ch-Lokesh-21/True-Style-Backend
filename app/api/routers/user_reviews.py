from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.api.deps import require_permission, get_current_user
from app.schemas.object_id import PyObjectId
from app.schemas.user_reviews import UserReviewsCreate, UserReviewsUpdate, UserReviewsOut
from app.crud import user_reviews as crud
from app.utils.gridfs import upload_image, replace_image, delete_image, _extract_file_id_from_url

router = APIRouter()  # mounted at /user-reviews


# ---------------------------
# Create (owner: current user)
# ---------------------------
@router.post(
    "/",
    response_model=UserReviewsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("user_reviews", "Create"))],
)
async def create_item(
    product_id: PyObjectId = Form(...),
    review_status_id: PyObjectId = Form(...),
    review: Optional[str] = Form(None),
    image: UploadFile = File(None),
    current_user: Dict = Depends(get_current_user),
):
    """
    Create user review for the current user. If an image file is provided, it's stored in GridFS.
    """
    try:
        image_url: Optional[str] = None
        if image is not None:
            _, image_url = await upload_image(image)

        payload = UserReviewsCreate(
            product_id=product_id,
            user_id=current_user["user_id"],   # enforce owner
            review_status_id=review_status_id,
            image_url=image_url,
            review=review,
        )
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        if "E11000" in str(e):
            raise HTTPException(status_code=409, detail="Duplicate review")
        raise HTTPException(status_code=500, detail=f"Failed to create UserReview: {e}")


# ---------------------------
# List (/reader)
# ---------------------------
@router.get(
    "/",
    response_model=List[UserReviewsOut],
    dependencies=[Depends(require_permission("user_reviews", "Read"))]
)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    product_id: Optional[PyObjectId] = Query(None),
    user_id: Optional[PyObjectId] = Query(None),
    review_status_id: Optional[PyObjectId] = Query(None),
):
    """
    Admin-style list with optional filters.
    """
    try:
        q: Dict[str, Any] = {}
        if product_id is not None:
            q["product_id"] = product_id
        if user_id is not None:
            q["user_id"] = user_id
        if review_status_id is not None:
            q["review_status_id"] = review_status_id
        return await crud.list_all(skip=skip, limit=limit, query=q or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list UserReviews: {e}")


# ---------------------------
# Get by _id (reader)
# ---------------------------
@router.get(
    "/{item_id}",
    response_model=UserReviewsOut,
    dependencies=[Depends(require_permission("user_reviews", "Read","admin"))],
)
async def get_item(item_id: PyObjectId):
    try:
        d = await crud.get_one(item_id)
        if not d:
            raise HTTPException(status_code=404, detail="UserReview not found")
        return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get UserReview: {e}")


# ----------------------------------------------------
# Get my review for a product (owner convenience route)
# ----------------------------------------------------
@router.get(
    "/by-product/{product_id}/me",
    response_model=UserReviewsOut,
    dependencies=[Depends(require_permission("user_reviews", "Read"))],
)
async def get_my_review_for_product(
    product_id: PyObjectId,
    current_user: Dict = Depends(get_current_user),
):
    try:
        item = await crud.get_by_user_and_product(
            user_id=current_user["user_id"], product_id=product_id
        )
        if not item:
            raise HTTPException(status_code=404, detail="UserReview not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get UserReview: {e}")


# ---------------------------
# Update (owner)
# ---------------------------
@router.put(
    "/{item_id}",
    response_model=UserReviewsOut,
    dependencies=[Depends(require_permission("user_reviews", "Update"))],
)
async def update_item(
    item_id: PyObjectId,
    product_id: Optional[PyObjectId] = Form(None),
    review_status_id: Optional[PyObjectId] = Form(None),
    review: Optional[str] = Form(None),
    image: UploadFile = File(None),
    current_user: Dict = Depends(get_current_user),
):
    """
    Owner update. If a new image is provided, replace the GridFS file and update image_url.
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=404, detail="UserReview not found")

        # owner check
        if str(current.user_id) != str(current_user["user_id"]):
            raise HTTPException(status_code=403, detail="Forbidden")

        patch = UserReviewsUpdate()

        if image is not None:
            old_id = _extract_file_id_from_url(current.image_url)
            if old_id:
                _, new_url = await replace_image(old_id, image)
            else:
                _, new_url = await upload_image(image)
            patch.image_url = new_url

        if product_id is not None:
            patch.product_id = product_id
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
        if "E11000" in str(e):
            raise HTTPException(status_code=409, detail="Duplicate review")
        raise HTTPException(status_code=500, detail=f"Failed to update UserReview: {e}")


# ---------------------------
# Delete (owner)
# ---------------------------
@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("user_reviews", "Delete"))],
)
async def delete_item(item_id: PyObjectId, current_user: Dict = Depends(get_current_user)):
    """
    Delete the review and clean up GridFS image if present.
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=404, detail="UserReview not found")

        if str(current.user_id) != str(current_user["user_id"]):
            raise HTTPException(status_code=403, detail="Forbidden")

        # delete DB first; then try file cleanup (best effort)
        ok = await crud.delete_one(item_id)
        if not ok:
            raise HTTPException(status_code=404, detail="UserReview not found")

        file_id = _extract_file_id_from_url(current.image_url)
        if file_id:
            try:
                await delete_image(file_id)
            except Exception:
                # swallow cleanup failures
                pass

        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete UserReview: {e}")


# ---------------------------
# Admin: list by status
# ---------------------------
@router.get(
    "/admin/by-status/{review_status_id}",
    response_model=List[UserReviewsOut],
    dependencies=[Depends(require_permission("user_reviews_admin", "Read","admin"))],
)
async def admin_list_by_status(
    review_status_id: PyObjectId,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    try:
        return await crud.list_all(
            skip=skip, limit=limit, query={"review_status_id": review_status_id}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list by status: {e}")


# ---------------------------
# Admin: change status
# ---------------------------
@router.post(
    "/admin/{item_id}/set-status/{review_status_id}",
    response_model=UserReviewsOut,
    dependencies=[Depends(require_permission("user_reviews_admin", "Update","admin"))],
)
async def admin_set_status(item_id: PyObjectId, review_status_id: PyObjectId):
    try:
        updated = await crud.admin_set_status(item_id=item_id, review_status_id=review_status_id)
        if not updated:
            raise HTTPException(status_code=404, detail="UserReview not found")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set status: {e}")


# ---------------------------
# Admin: force delete any
# ---------------------------
@router.delete(
    "/admin/{item_id}",
    dependencies=[Depends(require_permission("user_reviews_admin", "Delete","admin"))],
)
async def admin_force_delete(item_id: PyObjectId):
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=404, detail="UserReview not found")

        ok = await crud.delete_one(item_id)
        if not ok:
            raise HTTPException(status_code=404, detail="UserReview not found")

        file_id = _extract_file_id_from_url(current.image_url)
        if file_id:
            try:
                await delete_image(file_id)
            except Exception:
                pass

        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete UserReview: {e}")