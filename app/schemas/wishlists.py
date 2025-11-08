# app/schemas/wishlists.py
from __future__ import annotations
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from app.schemas.object_id import PyObjectId


class WishlistsBase(BaseModel):
    user_id: PyObjectId   # FK -> users._id

    model_config = {"extra": "ignore"}


class WishlistsCreate(WishlistsBase):
    pass


class WishlistsUpdate(BaseModel):
    user_id: Optional[PyObjectId] = None

    model_config = {"extra": "ignore"}


class WishlistsOut(WishlistsBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,          # _id <-> id aliasing
        "from_attributes": False,          # validate raw Mongo dicts
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }