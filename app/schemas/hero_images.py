# app/schemas/hero_images.py
from typing import Optional, Annotated
from datetime import datetime

from pydantic import BaseModel, Field, AnyUrl, TypeAdapter, field_validator
from app.schemas.object_id import PyObjectId

Idx = Annotated[int, Field(ge=0, le=1_000_000, description="Display order; non-negative.")]
ImageStr = Annotated[str, Field(max_length=2048, description="Image URL as plain string.")]

_URL = TypeAdapter(AnyUrl)  # validates http/https, localhost, custom ports, etc.


class HeroImagesBase(BaseModel):
    idx: Idx
    image_url: ImageStr

    @field_validator("image_url", mode="before")
    @classmethod
    def _validate_image_url(cls, v):
        # Validate as URL, then return plain str (Mongo-safe)
        return str(_URL.validate_python(v))

    model_config = {"extra": "ignore"}


class HeroImagesCreate(HeroImagesBase):
    pass


class HeroImagesUpdate(BaseModel):
    idx: Optional[Idx] = None
    image_url: Optional[ImageStr] = None

    @field_validator("image_url", mode="before")
    @classmethod
    def _validate_image_url(cls, v):
        if v is None:
            return v
        return str(_URL.validate_python(v))

    model_config = {"extra": "ignore"}


class HeroImagesOut(HeroImagesBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }