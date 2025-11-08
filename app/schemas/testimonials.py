# app/schemas/testimonials.py
from typing import Optional, Annotated
from datetime import datetime

from pydantic import BaseModel, Field, AnyUrl, TypeAdapter, field_validator
from app.schemas.object_id import PyObjectId

Idx = Annotated[int, Field(ge=0, le=1_000_000, description="Display order; non-negative.")]
ImageStr = Annotated[str, Field(max_length=2048, description="Image URL as plain string.")]
Description = Annotated[str, Field(min_length=1, max_length=2000, description="Non-empty, up to 2000 chars.")]

_URL = TypeAdapter(AnyUrl)  # accepts http/https, localhost, ports


class TestimonialsBase(BaseModel):
    idx: Idx
    image_url: ImageStr
    description: Description

    @field_validator("description", mode="before")
    @classmethod
    def _normalize_desc(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("description must not be empty.")
        return v

    @field_validator("image_url", mode="before")
    @classmethod
    def _validate_image_url(cls, v):
        return str(_URL.validate_python(v))  # validate then store as str (Mongo-safe)

    model_config = {"extra": "ignore"}


class TestimonialsCreate(TestimonialsBase):
    pass


class TestimonialsUpdate(BaseModel):
    idx: Optional[Idx] = None
    image_url: Optional[ImageStr] = None
    description: Optional[Description] = None

    @field_validator("description", mode="before")
    @classmethod
    def _normalize_desc(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("description must not be empty when provided.")
        return v

    @field_validator("image_url", mode="before")
    @classmethod
    def _validate_image_url(cls, v):
        if v is None:
            return v
        return str(_URL.validate_python(v))

    model_config = {"extra": "ignore"}


class TestimonialsOut(TestimonialsBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }