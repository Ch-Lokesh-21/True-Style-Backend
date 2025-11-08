# app/schemas/cards_1.py
from datetime import datetime
from typing import Optional, Annotated

from pydantic import BaseModel, Field, AnyUrl, TypeAdapter, field_validator, model_validator
from app.schemas.object_id import PyObjectId

# ---- Reusable constrained types ----
Idx = Annotated[int, Field(ge=0, le=1_000_000, description="Display order; non-negative.")]
Title = Annotated[str, Field(min_length=1, max_length=120, description="Title, 1–120 chars.")]
ImageStr = Annotated[str, Field(max_length=2048, description="Publicly reachable image URL.")]

# AnyUrl allows http/https, localhost, custom ports, etc.
_URL = TypeAdapter(AnyUrl)


class Cards1Base(BaseModel):
    idx: Idx
    title: Title
    image_url: ImageStr  # produced by build_file_url()

    @field_validator("title", mode="before")
    @classmethod
    def _normalize_title(cls, v):
        if isinstance(v, str):
            v = v.strip()
            # prevent empty-after-trim titles
            if not v:
                raise ValueError("title must not be empty.")
        return v

    @field_validator("image_url", mode="before")
    @classmethod
    def _validate_image_url(cls, v):
        # Validate as URL but return plain string so PyMongo doesn't see a Url object
        url = _URL.validate_python(v)
        return str(url)

    model_config = {"extra": "ignore"}


class Cards1Create(Cards1Base):
    pass


class Cards1Update(BaseModel):
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


class Cards1Out(Cards1Base):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }