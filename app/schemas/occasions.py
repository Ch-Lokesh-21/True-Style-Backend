# app/schemas/occasions.py
from typing import Optional, Annotated
from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from app.schemas.object_id import PyObjectId

OccasionName = Annotated[str, Field(min_length=1, max_length=120, description="Occasion name")]


class OccasionsBase(BaseModel):
    occasion: OccasionName

    @field_validator("occasion", mode="before")
    @classmethod
    def _normalize_occasion(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("occasion must not be empty.")
        return v

    model_config = {"extra": "ignore"}


class OccasionsCreate(OccasionsBase):
    pass


class OccasionsUpdate(BaseModel):
    occasion: Optional[OccasionName] = None

    @field_validator("occasion", mode="before")
    @classmethod
    def _normalize_occasion(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("occasion must not be empty when provided.")
        return v

    model_config = {"extra": "ignore"}


class OccasionsOut(OccasionsBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }