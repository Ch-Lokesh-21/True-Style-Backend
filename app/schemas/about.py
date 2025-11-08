from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, AnyUrl, field_validator
from app.schemas.object_id import PyObjectId


class AboutBase(BaseModel):
    idx: int = Field(ge=0)
    image_url: str
    description: str = Field(min_length=1, max_length=2000)

    @field_validator("image_url", mode="before")
    @classmethod
    def validate_image_url(cls, v):
        # Validate using AnyUrl, then return string value
        url = AnyUrl(v)
        return str(url)

    @field_validator("description", mode="before")
    @classmethod
    def strip_desc(cls, v):
        return v.strip() if isinstance(v, str) else v

    model_config = {"extra": "ignore"}


class AboutCreate(AboutBase):
    pass


class AboutUpdate(BaseModel):
    idx: Optional[int] = Field(default=None, ge=0)
    image_url: Optional[str] = None
    description: Optional[str] = Field(default=None, min_length=1, max_length=2000)

    @field_validator("image_url", mode="before")
    @classmethod
    def validate_image_url(cls, v):
        if v is None:
            return v
        url = AnyUrl(v)
        return str(url)

    @field_validator("description", mode="before")
    @classmethod
    def strip_desc(cls, v):
        return v.strip() if isinstance(v, str) else v

    model_config = {"extra": "ignore"}


class AboutOut(AboutBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }