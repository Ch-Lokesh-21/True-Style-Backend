# app/schemas/product_images.py
from typing import Optional, Annotated
from datetime import datetime

from pydantic import BaseModel, Field, AnyUrl, TypeAdapter, field_validator
from app.schemas.object_id import PyObjectId

ImageStr = Annotated[str, Field(max_length=2048, description="Image URL as plain string.")]
_URL = TypeAdapter(AnyUrl)  # accepts http/https, localhost, ports, etc.


class ProductImagesBase(BaseModel):
    product_id: PyObjectId
    image_url: ImageStr

    @field_validator("image_url", mode="before")
    @classmethod
    def _validate_image_url(cls, v):
        # Validate as URL, then return plain string (Mongo-safe)
        return str(_URL.validate_python(v))

    model_config = {"extra": "ignore"}


class ProductImagesCreate(ProductImagesBase):
    pass


class ProductImagesUpdate(BaseModel):
    product_id: Optional[PyObjectId] = None
    image_url: Optional[ImageStr] = None

    @field_validator("image_url", mode="before")
    @classmethod
    def _validate_image_url(cls, v):
        if v is None:
            return v
        return str(_URL.validate_python(v))

    model_config = {"extra": "ignore"}


class ProductImagesOut(ProductImagesBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }
