from datetime import datetime
from typing import Optional, Annotated

from pydantic import BaseModel, Field, field_validator
from app.schemas.object_id import PyObjectId

# Reusable constrained type
BrandName = Annotated[str, Field(min_length=1, max_length=120, description="Brand name")]


class BrandsBase(BaseModel):
    name: BrandName

    @field_validator("name", mode="before")
    @classmethod
    def _normalize_name(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("name must not be empty.")
        return v

    model_config = {"extra": "ignore"}


class BrandsCreate(BrandsBase):
    pass


class BrandsUpdate(BaseModel):
    name: Optional[BrandName] = None

    @field_validator("name", mode="before")
    @classmethod
    def _normalize_name(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("name must not be empty when provided.")
        return v

    model_config = {"extra": "ignore"}


class BrandsOut(BrandsBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,          # _id <-> id aliasing
        "from_attributes": False,          # validating raw Mongo dicts
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }
