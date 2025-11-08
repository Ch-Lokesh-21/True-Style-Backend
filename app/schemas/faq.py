from typing import Optional, Annotated
from datetime import datetime

from pydantic import BaseModel, Field, AnyUrl, TypeAdapter, field_validator
from app.schemas.object_id import PyObjectId

# Constrained reusable types
Idx = Annotated[int, Field(ge=0, le=1_000_000, description="Display order; non-negative.")]
Text = Annotated[str, Field(min_length=1, max_length=2000)]
ImageStr = Annotated[str, Field(max_length=2048)]

_URL = TypeAdapter(AnyUrl)  # allows http/https/localhost/ports & returns Url object


class FaqBase(BaseModel):
    idx: Idx
    image_url: ImageStr
    question: Text
    answer: Text

    # Trim text fields
    @field_validator("question", "answer", mode="before")
    @classmethod
    def _normalize_text(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Text fields cannot be empty.")
        return v

    # Validate and store Mongo-safe strings
    @field_validator("image_url", mode="before")
    @classmethod
    def _validate_url(cls, v):
        url = _URL.validate_python(v)
        return str(url)

    model_config = {"extra": "ignore"}


class FaqCreate(FaqBase):
    pass


class FaqUpdate(BaseModel):
    idx: Optional[Idx] = None
    image_url: Optional[ImageStr] = None
    question: Optional[Text] = None
    answer: Optional[Text] = None

    @field_validator("question", "answer", mode="before")
    @classmethod
    def _normalize_text(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Text fields cannot be empty when provided.")
        return v

    @field_validator("image_url", mode="before")
    @classmethod
    def _validate_url(cls, v):
        if v is None:
            return v
        url = _URL.validate_python(v)
        return str(url)

    model_config = {"extra": "ignore"}


class FaqOut(FaqBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }
