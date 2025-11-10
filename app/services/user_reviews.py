from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import HTTPException, UploadFile, status

from app.schemas.object_id import PyObjectId
from app.schemas.user_reviews import UserReviewsCreate, UserReviewsUpdate, UserReviewsOut
from app.crud import user_reviews as crud
from app.utils.gridfs import upload_image, replace_image, delete_image, _extract_file_id_from_url


# Create (owner=current_user)
async def create_user_review(
    product_id: PyObjectId,
    review_status_id: PyObjectId,
    review: Optional[str],
    image: Optional[UploadFile],
    current_user: Dict,
) -> UserReviewsOut:
    try:
        image_url: Optional[str] = None
        if image is not None:
            _, image_url = await upload_image(image)

        payload = UserReviewsCreate(
            product_id=product_id,
            user_id=current_user["user_id"],
            review_status_id=review_status_id,
            image_url=image_url,
            review=review,
        )
        return await crud.create(payload)
    except HTTPException:
        raise
    except Exception as e:
        if "E11000" in str(e):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate review")
        raise HTTPException(status_code=500, detail=f"Failed to create UserReview: {e}")


# List with filters
async def list_user_reviews(
    skip: int,
    limit: int,
    product_id: Optional[PyObjectId],
    user_id: Optional[PyObjectId],
    review_status_id: Optional[PyObjectId],
) -> List[UserReviewsOut]:
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


# Admin get by _id
async def get_user_review_admin(item_id: PyObjectId) -> UserReviewsOut:
    try:
        d = await crud.get_one(item_id)
        if not d:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="UserReview not found")
        return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get UserReview: {e}")


# My review for a product
async def get_my_review_for_product_service(product_id: PyObjectId, current_user: Dict) -> UserReviewsOut:
    try:
        item = await crud.get_by_user_and_product(
            user_id=current_user["user_id"], product_id=product_id
        )
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="UserReview not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get UserReview: {e}")


# Update (owner)
async def update_user_review(
    item_id: PyObjectId,
    product_id: Optional[PyObjectId],
    review_status_id: Optional[PyObjectId],
    review: Optional[str],
    image: Optional[UploadFile],
    current_user: Dict,
) -> UserReviewsOut:
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="UserReview not found")

        if str(current.user_id) != str(current_user["user_id"]):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

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
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")

        updated = await crud.update_one(item_id, patch)
        if not updated:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Update failed")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        if "E11000" in str(e):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate review")
        raise HTTPException(status_code=500, detail=f"Failed to update UserReview: {e}")


# Delete (owner)
async def delete_user_review(item_id: PyObjectId, current_user: Dict) -> bool:
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="UserReview not found")

        if str(current.user_id) != str(current_user["user_id"]):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        ok = await crud.delete_one(item_id)
        if not ok:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="UserReview not found")

        file_id = _extract_file_id_from_url(current.image_url)
        if file_id:
            try:
                await delete_image(file_id)
            except Exception:
                pass
        return True
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete UserReview: {e}")


# Admin: list by status
async def admin_list_by_status_service(
    review_status_id: PyObjectId,
    skip: int,
    limit: int,
) -> List[UserReviewsOut]:
    try:
        return await crud.list_all(
            skip=skip, limit=limit, query={"review_status_id": review_status_id}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list by status: {e}")


# Admin: change status
async def admin_set_status_service(item_id: PyObjectId, review_status_id: PyObjectId) -> UserReviewsOut:
    try:
        updated = await crud.admin_set_status(item_id=item_id, review_status_id=review_status_id)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="UserReview not found")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set status: {e}")


# Admin: force delete any
async def admin_force_delete_service(item_id: PyObjectId) -> bool:
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="UserReview not found")

        ok = await crud.delete_one(item_id)
        if not ok:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="UserReview not found")

        file_id = _extract_file_id_from_url(current.image_url)
        if file_id:
            try:
                await delete_image(file_id)
            except Exception:
                pass
        return True
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete UserReview: {e}")