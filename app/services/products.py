"""
Service layer for Products.

Centralizes:
- Validation of numeric ranges and input consistency
- GridFS image upload/replace/cleanup
- Calls to CRUD
- Error mapping and HTTP semantics

Router keeps UploadFile as File(.../None) for docs; service signatures accept
`thumbnail: UploadFile = None` when optional.
"""

from __future__ import annotations
from typing import List, Optional

from fastapi import HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.schemas.object_id import PyObjectId
from app.schemas.products import ProductsCreate, ProductsUpdate, ProductsOut
from app.crud import products as crud
from app.utils.gridfs import (
    upload_image, replace_image, delete_image, _extract_file_id_from_url
)


# ---------------------- helpers ----------------------
def _validate_numeric_ranges(
    *,
    price: Optional[float] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    gst_percentage: Optional[int] = None,
    gst_amount: Optional[float] = None,
    total_price: Optional[float] = None,
    rating: Optional[float] = None,
    quantity: Optional[int] = None,
) -> None:
    """
    Validate numeric fields across product operations.

    Raises:
        HTTPException(400) if any constraint fails.
    """
    if quantity is not None and quantity < 0:
        raise HTTPException(status_code=400, detail="quantity must be >= 0")
    if price is not None and price < 0:
        raise HTTPException(status_code=400, detail="price must be >= 0")
    if min_price is not None and min_price < 0:
        raise HTTPException(status_code=400, detail="min_price must be >= 0")
    if max_price is not None and max_price < 0:
        raise HTTPException(status_code=400, detail="max_price must be >= 0")
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=400, detail="min_price cannot exceed max_price")
    if gst_percentage is not None and not (0 <= gst_percentage <= 100):
        raise HTTPException(status_code=400, detail="gst_percentage must be between 0 and 100")
    if gst_amount is not None and gst_amount < 0:
        raise HTTPException(status_code=400, detail="gst_amount must be >= 0")
    if total_price is not None and total_price < 0:
        raise HTTPException(status_code=400, detail="total_price must be >= 0")
    if rating is not None and not (0.0 <= rating <= 5.0):
        raise HTTPException(status_code=400, detail="rating must be between 0 and 5")


async def _cleanup_gridfs_urls(urls: list[str]) -> list[str]:
    """
    Best-effort deletion of GridFS files for given URLs.

    Returns:
        List of warning strings for non-fatal cleanup errors.
    """
    warnings: list[str] = []
    for url in urls or []:
        try:
            file_id = _extract_file_id_from_url(url)
            if file_id:
                await delete_image(file_id)
        except Exception as ex:
            warnings.append(f"{url}: {ex}")
    return warnings


# ---------------------- services ----------------------
async def create_item_service(
    *,
    brand_id: PyObjectId,
    occasion_id: PyObjectId,
    category_id: PyObjectId,
    product_type_id: PyObjectId,
    name: str,
    description: str,
    price: float,
    hsn_code: int,
    gst_percentage: int,
    gst_amount: float,
    total_price: float,
    color: str,
    quantity: int,
    thumbnail: UploadFile,   # required here
) -> ProductsOut:
    """
    Create a product and upload its thumbnail.

    Raises:
        400 on validation / missing thumbnail
        500 on persistence failures
    """
    _validate_numeric_ranges(
        price=price,
        gst_percentage=gst_percentage,
        gst_amount=gst_amount,
        total_price=total_price,
        quantity=quantity,
    )

    if not thumbnail or not thumbnail.filename:
        raise HTTPException(status_code=400, detail="thumbnail file is required")

    try:
        _, url = await upload_image(thumbnail)

        payload = ProductsCreate(
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
            out_of_stock=(quantity == 0),
            quantity=quantity,
            thumbnail_url=url,
        )

        created = await crud.create(payload)
        if not created:
            raise HTTPException(status_code=500, detail="Failed to persist Product")
        return created

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create Product: {e}")


async def list_items_service(
    *,
    skip: int,
    limit: int,
    q: Optional[str],
    brand_id: Optional[PyObjectId],
    category_id: Optional[PyObjectId],
    occasion_id: Optional[PyObjectId],
    product_type_id: Optional[PyObjectId],
    color: Optional[str],
    out_of_stock: Optional[bool],
    min_price: Optional[float],
    max_price: Optional[float],
) -> List[ProductsOut]:
    """
    List products with filters and pagination.
    """
    _validate_numeric_ranges(min_price=min_price, max_price=max_price)
    try:
        return await crud.list_all(
            skip=skip, limit=limit, q=q,
            brand_id=brand_id, category_id=category_id,
            occasion_id=occasion_id, product_type_id=product_type_id,
            color=color, out_of_stock=out_of_stock,
            min_price=min_price, max_price=max_price,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list products: {e}")


async def get_item_service(item_id: PyObjectId) -> ProductsOut:
    """
    Get a product by ObjectId.

    Raises:
        404 if not found.
    """
    try:
        d = await crud.get_one(item_id)
        if not d:
            raise HTTPException(status_code=404, detail="Product not found")
        return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get product: {e}")


async def update_item_service(
    *,
    item_id: PyObjectId,
    brand_id: Optional[PyObjectId] = None,
    occasion_id: Optional[PyObjectId] = None,
    category_id: Optional[PyObjectId] = None,
    product_type_id: Optional[PyObjectId] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    rating: Optional[float] = None,
    price: Optional[float] = None,
    hsn_code: Optional[int] = None,
    gst_percentage: Optional[int] = None,
    gst_amount: Optional[float] = None,
    total_price: Optional[float] = None,
    color: Optional[str] = None,
    out_of_stock: Optional[bool] = None,
    thumbnail: UploadFile = None,  # optional in service to show upload in docs
    quantity: Optional[int] = None,
) -> ProductsOut:
    """
    Update product fields and optionally replace thumbnail (GridFS).

    - Keeps `out_of_stock` synchronized with `quantity` when only one is provided.

    Raises:
        400 when no fields provided or invalid ranges.
        404 if product not found.
        409 on generic update failure (e.g., concurrent delete).
    """
    try:
        current = await crud.get_one(item_id)
        if not current:
            raise HTTPException(status_code=404, detail="Product not found")

        _validate_numeric_ranges(
            price=price, gst_percentage=gst_percentage,
            gst_amount=gst_amount, total_price=total_price,
            rating=rating, quantity=quantity
        )

        patch = ProductsUpdate()

        if thumbnail is not None:
            old_id = _extract_file_id_from_url(current.thumbnail_url)
            if old_id:
                _, new_url = await replace_image(old_id, thumbnail)
            else:
                _, new_url = await upload_image(thumbnail)
            patch.thumbnail_url = new_url  # type: ignore[attr-defined]

        if brand_id is not None:
            patch.brand_id = brand_id
        if occasion_id is not None:
            patch.occasion_id = occasion_id
        if category_id is not None:
            patch.category_id = category_id
        if product_type_id is not None:
            patch.product_type_id = product_type_id
        if name is not None:
            patch.name = name
        if description is not None:
            patch.description = description
        if rating is not None:
            patch.rating = rating
        if price is not None:
            patch.price = price
        if hsn_code is not None:
            patch.hsn_code = hsn_code
        if gst_percentage is not None:
            patch.gst_percentage = gst_percentage
        if gst_amount is not None:
            patch.gst_amount = gst_amount
        if total_price is not None:
            patch.total_price = total_price
        if color is not None:
            patch.color = color
        if quantity is not None:
            patch.quantity = quantity
            if out_of_stock is None:
                patch.out_of_stock = (quantity == 0)
        if out_of_stock is not None:
            patch.out_of_stock = out_of_stock
            if out_of_stock and quantity is None:
                patch.quantity = 0

        if not any(v is not None for v in patch.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")

        updated = await crud.update_one(item_id, patch)
        if not updated:
            raise HTTPException(status_code=409, detail="Update failed")
        return updated

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update product: {e}")


async def delete_item_service(item_id: PyObjectId):
    """
    Cascade delete a product and related documents,
    then best-effort cleanup of related GridFS files (thumbnails, product images).

    Returns:
        JSONResponse({"deleted": True, "file_cleanup_warnings": [...]?})

    Raises:
        404 if not found.
        500 on unexpected failures.
    """
    try:
        result = await crud.delete_one_cascade(item_id)
        if not result or result.get("status") == "not_found":
            raise HTTPException(status_code=404, detail="Product not found")
        if result.get("status") != "deleted":
            raise HTTPException(status_code=500, detail="Failed to delete product")

        warnings = await _cleanup_gridfs_urls(result.get("image_urls", []))
        payload = {"deleted": True}
        if warnings:
            payload["file_cleanup_warnings"] = warnings
        return JSONResponse(status_code=200, content=payload)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete product: {e}")