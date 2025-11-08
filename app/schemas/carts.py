# app/schemas/carts.py
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field
from app.schemas.object_id import PyObjectId


class CartsBase(BaseModel):
    user_id: PyObjectId  # FK to users._id

    model_config = {"extra": "ignore"}


class CartsCreate(CartsBase):
    pass


class CartsUpdate(BaseModel):
    user_id: Optional[PyObjectId] = None  # partial update allowed

    model_config = {"extra": "ignore"}


class CartsOut(CartsBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }