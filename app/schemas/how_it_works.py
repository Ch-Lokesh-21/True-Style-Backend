from typing import Optional, Annotated
from datetime import datetime

from pydantic import BaseModel, Field, AnyUrl, TypeAdapter, field_validator
from app.schemas.object_id import PyObjectId

Idx = Annotated[int, Field(ge=0, le=1_000_000, description="Display order (non-negative).")]
Title = Annotated[str, Field(min_length=1, max_length=200, description="Title, 1–200 chars.")]
ImageStr = Annotated[str, Field(max_length=2048, description="Image URL (string).")]

_URL = TypeAdapter(AnyUrl)


class HowItWorksBase(BaseModel):
    idx: Idx
    image_url: ImageStr
    title: Title

    @field_validator("title", mode="before")
    @classmethod
    def _normalize_title(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("title must not be empty")
        return v

    @field_validator("image_url", mode="before")
    @classmethod
    def _validate_image_url(cls, v):
        # ensure valid URL and store as plain string
        return str(_URL.validate_python(v))

    model_config = {"extra": "ignore"}


class HowItWorksCreate(HowItWorksBase):
    pass


class HowItWorksUpdate(BaseModel):
    idx: Optional[Idx] = None
    image_url: Optional[ImageStr] = None
    title: Optional[Title] = None

    @field_validator("title", mode="before")
    @classmethod
    def _normalize_title(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("title must not be empty when provided")
        return v

    @field_validator("image_url", mode="before")
    @classmethod
    def _validate_image_url(cls, v):
        if v is None:
            return v
        return str(_URL.validate_python(v))

    model_config = {"extra": "ignore"}


class HowItWorksOut(HowItWorksBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }