# app/schemas/user_reviews.py
from typing import Optional, Annotated
from datetime import datetime

from pydantic import BaseModel, Field, AnyUrl, TypeAdapter, field_validator
from app.schemas.object_id import PyObjectId

# Reusable constrained types
ReviewText = Annotated[str, Field(min_length=1, max_length=4000, description="Review text")]
ImageUrlStr = Annotated[str, Field(max_length=2048, description="Image URL as plain string")]

_URL = TypeAdapter(AnyUrl)  # validates http/https, localhost, custom ports, etc.


class UserReviewsBase(BaseModel):
    product_id: PyObjectId
    user_id: PyObjectId
    review_status_id: PyObjectId
    image_url: Optional[ImageUrlStr] = None
    review: Optional[ReviewText] = None

    @field_validator("image_url", mode="before")
    @classmethod
    def _validate_image_url(cls, v):
        if v is None:
            return v
        return str(_URL.validate_python(v))

    @field_validator("review", mode="before")
    @classmethod
    def _normalize_review(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                # Empty string after trimming should be rejected; use None to skip updating
                raise ValueError("review must not be empty when provided.")
        return v

    model_config = {"extra": "ignore"}


class UserReviewsCreate(UserReviewsBase):
    pass


class UserReviewsUpdate(BaseModel):
    product_id: Optional[PyObjectId] = None
    user_id: Optional[PyObjectId] = None
    review_status_id: Optional[PyObjectId] = None
    image_url: Optional[ImageUrlStr] = None
    review: Optional[ReviewText] = None

    @field_validator("image_url", mode="before")
    @classmethod
    def _validate_image_url(cls, v):
        if v is None:
            return v
        return str(_URL.validate_python(v))

    @field_validator("review", mode="before")
    @classmethod
    def _normalize_review(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("review must not be empty when provided.")
        return v

    model_config = {"extra": "ignore"}


class UserReviewsOut(UserReviewsBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }