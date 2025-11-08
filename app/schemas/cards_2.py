# app/schemas/cards_2.py
from typing import Optional, Annotated
from datetime import datetime

from pydantic import BaseModel, Field, AnyUrl, TypeAdapter, field_validator
from app.schemas.object_id import PyObjectId

# Reusable constrained types
Idx = Annotated[int, Field(ge=0, le=1_000_000, description="Display order; non-negative.")]
Title = Annotated[str, Field(min_length=1, max_length=120, description="Title, 1–120 chars.")]
ImageStr = Annotated[str, Field(max_length=2048, description="Image URL as string.")]

# AnyUrl allows http/https, localhost, custom ports, etc.
_URL = TypeAdapter(AnyUrl)


class Cards2Base(BaseModel):
    idx: Idx
    image_url: ImageStr
    title: Title

    @field_validator("title", mode="before")
    @classmethod
    def _normalize_title(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("title must not be empty.")
        return v

    @field_validator("image_url", mode="before")
    @classmethod
    def _validate_image_url(cls, v):
        # Validate as URL, then store as plain string (Mongo-safe)
        url = _URL.validate_python(v)
        return str(url)

    model_config = {"extra": "ignore"}


class Cards2Create(Cards2Base):
    pass


class Cards2Update(BaseModel):
    idx: Optional[Idx] = None
    title: Optional[Title] = None
    image_url: Optional[ImageStr] = None

    @field_validator("title", mode="before")
    @classmethod
    def _normalize_title(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("title must not be empty when provided.")
        return v

    @field_validator("image_url", mode="before")
    @classmethod
    def _validate_image_url(cls, v):
        if v is None:
            return v
        url = _URL.validate_python(v)
        return str(url)

    model_config = {"extra": "ignore"}


class Cards2Out(Cards2Base):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }
