from __future__ import annotations
from typing import List, Optional

from bson import ObjectId
from fastapi import (
    APIRouter, Depends, HTTPException, Query, status,
    UploadFile, File, Form
)
from fastapi.responses import JSONResponse

from app.api.deps import require_permission
from app.schemas.object_id import PyObjectId
from app.schemas.products import ProductsCreate, ProductsUpdate, ProductsOut
from app.crud import products as crud
from app.utils.gridfs import (
    upload_image, replace_image, delete_image, _extract_file_id_from_url
)

router = APIRouter()


def _validate_numeric_ranges(
    price: Optional[float] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    gst_percentage: Optional[int] = None,
    gst_amount: Optional[float] = None,
    total_price: Optional[float] = None,
    rating: Optional[float] = None,
    quantity: Optional[int] = None,
) -> None:
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
    warnings: list[str] = []
    for url in urls or []:
        try:
            file_id = _extract_file_id_from_url(url)
            if file_id:
                await delete_image(file_id)
        except Exception as ex:
            warnings.append(f"{url}: {ex}")
    return warnings


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
    Create product: all FKs are real ObjectId via PyObjectId; thumbnail stored in GridFS.
    """
    _validate_numeric_ranges(
        price=price, gst_percentage=gst_percentage,
        gst_amount=gst_amount, total_price=total_price,
        quantity=quantity
    )
    if not thumbnail or not thumbnail.filename:
        raise HTTPException(status_code=400, detail="thumbnail file is required")

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
        out_of_stock=quantity == 0,
        quantity=quantity,
        thumbnail_url=url,
    )
    created = await crud.create(payload)
    if not created:
        raise HTTPException(status_code=500, detail="Failed to persist Product")
    return created


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
    _validate_numeric_ranges(min_price=min_price, max_price=max_price)
    return await crud.list_all(
        skip=skip, limit=limit, q=q,
        brand_id=brand_id, category_id=category_id,
        occasion_id=occasion_id, product_type_id=product_type_id,
        color=color, out_of_stock=out_of_stock,
        min_price=min_price, max_price=max_price,
    )


@router.get("/{item_id}", response_model=ProductsOut)
async def get_item(item_id: PyObjectId):
    d = await crud.get_one(item_id)
    if not d:
        raise HTTPException(status_code=404, detail="Product not found")
    return d


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
    thumbnail: UploadFile = File(None),
    quantity: Optional[int] = Form(None),
):
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
        _, new_url = await (replace_image(old_id, thumbnail) if old_id else upload_image(thumbnail))
        patch.thumbnail_url = new_url

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
        # keep out_of_stock in sync if client passed both
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


@router.delete(
    "/{item_id}",
    dependencies=[Depends(require_permission("products", "Delete"))],
)
async def delete_item(item_id: PyObjectId):
    """
    Cascade delete product + related docs (all using real ObjectId FKs).
    After commit, best-effort GridFS cleanup.
    """
    result = await crud.delete_one_cascade(item_id)
    if not result or result["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Product not found")
    if result["status"] != "deleted":
        raise HTTPException(status_code=500, detail="Failed to delete product")

    warnings = await _cleanup_gridfs_urls(result.get("image_urls", []))
    payload = {"deleted": True}
    if warnings:
        payload["file_cleanup_warnings"] = warnings
    return JSONResponse(status_code=200, content=payload)