# app/schemas/user_ratings.py
from __future__ import annotations
from typing import Optional, Annotated
from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from app.schemas.object_id import PyObjectId

Rating = Annotated[float, Field(ge=0, le=5, description="Star rating from 0 to 5")]

class UserRatingsBase(BaseModel):
    product_id: PyObjectId
    user_id: PyObjectId
    rating: Optional[Rating] = None  # keep optional as in your original

    model_config = {"extra": "ignore"}


class UserRatingsCreate(UserRatingsBase):
    pass
    # If you want rating required on create:
    # rating: Rating


class UserRatingsUpdate(BaseModel):
    product_id: Optional[PyObjectId] = None
    user_id: Optional[PyObjectId] = None
    rating: Optional[Rating] = None

    model_config = {"extra": "ignore"}


class UserRatingsOut(UserRatingsBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,          # _id <-> id aliasing
        "from_attributes": False,          # validate raw Mongo dicts
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }