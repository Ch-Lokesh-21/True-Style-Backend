# app/schemas/wishlist_items.py
from __future__ import annotations
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from app.schemas.object_id import PyObjectId


class WishlistItemsBase(BaseModel):
    wishlist_id: PyObjectId   # FK -> wishlists._id
    product_id: PyObjectId    # FK -> products._id

    model_config = {"extra": "ignore"}


class WishlistItemsCreate(WishlistItemsBase):
    pass


class WishlistItemsUpdate(BaseModel):
    wishlist_id: Optional[PyObjectId] = None
    product_id: Optional[PyObjectId] = None

    model_config = {"extra": "ignore"}


class WishlistItemsOut(WishlistItemsBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }