"""
Routes for Products.

This module exposes HTTP endpoints for product CRUD:
- Thin layer that parses inputs, applies RBAC, and delegates to the service layer.
- Keeps UploadFile parameters as `File(.../None)` so Swagger shows the file picker.

All business logic lives in `app.services.products`.
"""

from __future__ import annotations
from typing import List, Optional

from fastapi import (
    APIRouter, Depends, HTTPException, Query, status,
    UploadFile, File, Form
)
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.products import ProductsOut
from app.services.products import (
    create_item_service,
    list_items_service,
    get_item_service,
    update_item_service,
    delete_item_service,
)

router = APIRouter()


@router.post(
    "/",
    response_model=ProductsOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("products", "Create"))],
)
async def create_item(
    brand_id: PyObjectId = Form(...),
    occasion_id: PyObjectId = Form(...),
    category_id: PyObjectId = Form(...),
    product_type_id: PyObjectId = Form(...),
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    hsn_code: int = Form(...),
    gst_percentage: int = Form(...),
    gst_amount: float = Form(...),
    total_price: float = Form(...),
    color: str = Form(...),
    quantity: int = Form(...),
    thumbnail: UploadFile = File(...),
):
    """
    Create a product.

    - Validates numeric ranges.
    - Ensures thumbnail file is provided.
    - Uploads thumbnail to GridFS and persists URL.
    - Marks `out_of_stock=True` if `quantity==0`.

    Returns:
        ProductsOut
    """
    return await create_item_service(
        brand_id=brand_id,
        occasion_id=occasion_id,
        category_id=category_id,
        product_type_id=product_type_id,
        name=name,
        description=description,
        price=price,
        hsn_code=hsn_code,
        gst_percentage=gst_percentage,
        gst_amount=gst_amount,
        total_price=total_price,
        color=color,
        quantity=quantity,
        thumbnail=thumbnail,   # required in router
    )


@router.get("/", response_model=List[ProductsOut])
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    q: Optional[str] = Query(None, description="Search name/description (case-insensitive)"),
    brand_id: Optional[PyObjectId] = Query(None),
    category_id: Optional[PyObjectId] = Query(None),
    occasion_id: Optional[PyObjectId] = Query(None),
    product_type_id: Optional[PyObjectId] = Query(None),
    color: Optional[str] = Query(None),
    out_of_stock: Optional[bool] = Query(None),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
):
    """
    List products with rich filters and pagination.

    Notes:
        - Validates min_price/max_price relationship.
    """
    return await list_items_service(
        skip=skip, limit=limit, q=q,
        brand_id=brand_id, category_id=category_id,
        occasion_id=occasion_id, product_type_id=product_type_id,
        color=color, out_of_stock=out_of_stock,
        min_price=min_price, max_price=max_price,
    )


@router.get("/{item_id}", response_model=ProductsOut)
async def get_item(item_id: PyObjectId):
    """
    Get a single product by id.

    Raises:
        404 if not found.
    """
    return await get_item_service(item_id)


@router.put(
    "/{item_id}",
    response_model=ProductsOut,
    dependencies=[Depends(require_permission("products", "Update"))],
)
async def update_item(
    item_id: PyObjectId,
    brand_id: Optional[PyObjectId] = Form(None),
    occasion_id: Optional[PyObjectId] = Form(None),
    category_id: Optional[PyObjectId] = Form(None),
    product_type_id: Optional[PyObjectId] = Form(None),
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    rating: Optional[float] = Form(None),
    price: Optional[float] = Form(None),
    hsn_code: Optional[int] = Form(None),
    gst_percentage: Optional[int] = Form(None),
    gst_amount: Optional[float] = Form(None),
    total_price: Optional[float] = Form(None),
    color: Optional[str] = Form(None),
    out_of_stock: Optional[bool] = Form(None),
    thumbnail: UploadFile = File(None),  # optional in router to show upload control
    quantity: Optional[int] = Form(None),
):
    """
    Update product fields.

    - Validates numeric ranges.
    - If `thumbnail` provided, replaces GridFS file and updates `thumbnail_url`.
    - Keeps `out_of_stock` in sync with `quantity` when one is provided without the other.
    """
    return await update_item_service(
        item_id=item_id,
        brand_id=brand_id,
        occasion_id=occasion_id,
        category_id=category_id,
        product_type_id=product_type_id,
        name=name,
        description=description,
        rating=rating,
        price=price,
        hsn_code=hsn_code,
        gst_percentage=gst_percentage,
        gst_amount=gst_amount,
        total_price=total_price,
        color=color,
        out_of_stock=out_of_stock,
        thumbnail=thumbnail,   # optional in router
        quantity=quantity,
    )


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("products", "Delete"))],
)
async def delete_item(item_id: PyObjectId):
    """
    Cascade delete a product and related documents.
    After commit, performs best-effort GridFS cleanup of associated images.

    Returns:
        JSONResponse({"deleted": True, "file_cleanup_warnings": [...]?})
    """
    return await delete_item_service(item_id)