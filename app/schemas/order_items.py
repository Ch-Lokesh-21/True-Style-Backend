# app/schemas/order_items.py
from typing import Optional, Annotated
from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from app.schemas.object_id import PyObjectId

Qty = Annotated[int, Field(ge=1, le=1_000_000, description="Quantity must be ≥ 1")]
Size = Annotated[str, Field(min_length=1, max_length=50, description="Size label (e.g., S, M, L, 42)")]


class OrderItemsBase(BaseModel):
    order_id: PyObjectId
    product_id: PyObjectId
    quantity: Optional[Qty] = None
    size: Optional[Size] = None
    user_id: PyObjectId

    @field_validator("size", mode="before")
    @classmethod
    def _trim_size(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v == "":
                raise ValueError("size must not be empty when provided.")
        return v

    model_config = {"extra": "ignore"}


class OrderItemsCreate(OrderItemsBase):
    pass


class OrderItemsUpdate(BaseModel):
    order_id: Optional[PyObjectId] = None
    product_id: Optional[PyObjectId] = None
    quantity: Optional[Qty] = None
    size: Optional[Size] = None
    user_id: Optional[PyObjectId] = None

    @field_validator("size", mode="before")
    @classmethod
    def _trim_size(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v == "":
                raise ValueError("size must not be empty when provided.")
        return v

    model_config = {"extra": "ignore"}


class OrderItemsOut(OrderItemsBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }