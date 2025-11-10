from __future__ import annotations
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.api.deps import require_permission, get_current_user
from app.schemas.object_id import PyObjectId
from app.schemas.user_reviews import UserReviewsCreate, UserReviewsUpdate, UserReviewsOut
from app.services.user_reviews import (
    create_user_review,
    list_user_reviews,
    get_user_review_admin,
    get_my_review_for_product_service,
    update_user_review,
    delete_user_review,
    admin_list_by_status_service,
    admin_set_status_service,
    admin_force_delete_service,
)

router = APIRouter()  # mounted at /user-reviews


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
    return await create_user_review(
        product_id=product_id,
        review_status_id=review_status_id,
        review=review,
        image=image,
        current_user=current_user,
    )


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
    return await list_user_reviews(skip=skip, limit=limit,
                                   product_id=product_id, user_id=user_id, review_status_id=review_status_id)


@router.get(
    "/{item_id}",
    response_model=UserReviewsOut,
    dependencies=[Depends(require_permission("user_reviews", "Read","admin"))],
)
async def get_item(item_id: PyObjectId):
    return await get_user_review_admin(item_id=item_id)


@router.get(
    "/by-product/{product_id}/me",
    response_model=UserReviewsOut,
    dependencies=[Depends(require_permission("user_reviews", "Read"))],
)
async def get_my_review_for_product(
    product_id: PyObjectId,
    current_user: Dict = Depends(get_current_user),
):
    return await get_my_review_for_product_service(product_id=product_id, current_user=current_user)


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
    return await update_user_review(
        item_id=item_id,
        product_id=product_id,
        review_status_id=review_status_id,
        review=review,
        image=image,
        current_user=current_user,
    )


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("user_reviews", "Delete"))],
)
async def delete_item(item_id: PyObjectId, current_user: Dict = Depends(get_current_user)):
    ok = await delete_user_review(item_id=item_id, current_user=current_user)
    if ok:
        return JSONResponse(status_code=200, content={"deleted": True})


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
    return await admin_list_by_status_service(review_status_id=review_status_id, skip=skip, limit=limit)


@router.post(
    "/admin/{item_id}/set-status/{review_status_id}",
    response_model=UserReviewsOut,
    dependencies=[Depends(require_permission("user_reviews_admin", "Update","admin"))],
)
async def admin_set_status(item_id: PyObjectId, review_status_id: PyObjectId):
    return await admin_set_status_service(item_id=item_id, review_status_id=review_status_id)


@router.delete(
    "/admin/{item_id}",
    dependencies=[Depends(require_permission("user_reviews_admin", "Delete","admin"))],
)
async def admin_force_delete(item_id: PyObjectId):
    ok = await admin_force_delete_service(item_id=item_id)
    if ok:
        return JSONResponse(status_code=200, content={"deleted": True})