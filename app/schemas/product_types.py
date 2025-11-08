# app/schemas/product_types.py
from typing import Optional, Annotated
from datetime import datetime

from pydantic import BaseModel, Field, AnyUrl, TypeAdapter, field_validator
from app.schemas.object_id import PyObjectId

TypeName = Annotated[str, Field(min_length=1, max_length=120, description="Product type name, 1–120 chars.")]
UrlStr = Annotated[str, Field(max_length=2048, description="URL as plain string.")]

_URL = TypeAdapter(AnyUrl)  # allows http/https, localhost, custom ports


class ProductTypesBase(BaseModel):
    type: TypeName
    size_chart_url: UrlStr
    thumbnail_url: UrlStr

    @field_validator("type", mode="before")
    @classmethod
    def _normalize_type(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("type must not be empty.")
        return v

    @field_validator("size_chart_url", "thumbnail_url", mode="before")
    @classmethod
    def _validate_urls(cls, v):
        # Validate as URL, then return plain string (Mongo-safe)
        return str(_URL.validate_python(v))

    model_config = {"extra": "ignore"}


class ProductTypesCreate(ProductTypesBase):
    pass


class ProductTypesUpdate(BaseModel):
    type: Optional[TypeName] = None
    size_chart_url: Optional[UrlStr] = None
    thumbnail_url: Optional[UrlStr] = None

    @field_validator("type", mode="before")
    @classmethod
    def _normalize_type(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("type must not be empty when provided.")
        return v

    @field_validator("size_chart_url", "thumbnail_url", mode="before")
    @classmethod
    def _validate_urls(cls, v):
        if v is None:
            return v
        return str(_URL.validate_python(v))

    model_config = {"extra": "ignore"}


class ProductTypesOut(ProductTypesBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }