# app/schemas/policies.py
from typing import Optional, Annotated
from datetime import datetime

from pydantic import BaseModel, Field, AnyUrl, TypeAdapter, field_validator
from app.schemas.object_id import PyObjectId

# Reusable constrained types
Idx = Annotated[int, Field(ge=0, le=1_000_000, description="Display order; non-negative.")]
Title = Annotated[str, Field(min_length=1, max_length=200, description="Title, 1–200 chars.")]
Description = Annotated[str, Field(min_length=1, max_length=4000, description="Description, 1–4000 chars.")]
ImageStr = Annotated[str, Field(max_length=2048, description="Image URL as string.")]

_URL = TypeAdapter(AnyUrl)  # accepts http/https, localhost, custom ports, etc.


class PoliciesBase(BaseModel):
    idx: Idx
    image_url: ImageStr
    description: Description
    title: Title

    @field_validator("title", "description", mode="before")
    @classmethod
    def _normalize_text(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Field cannot be empty.")
        return v

    @field_validator("image_url", mode="before")
    @classmethod
    def _validate_image_url(cls, v):
        return str(_URL.validate_python(v))

    model_config = {"extra": "ignore"}


class PoliciesCreate(PoliciesBase):
    pass


class PoliciesUpdate(BaseModel):
    idx: Optional[Idx] = None
    image_url: Optional[ImageStr] = None
    description: Optional[Description] = None
    title: Optional[Title] = None

    @field_validator("title", "description", mode="before")
    @classmethod
    def _normalize_text(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Field cannot be empty when provided.")
        return v

    @field_validator("image_url", mode="before")
    @classmethod
    def _validate_image_url(cls, v):
        if v is None:
            return v
        return str(_URL.validate_python(v))

    model_config = {"extra": "ignore"}


class PoliciesOut(PoliciesBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }