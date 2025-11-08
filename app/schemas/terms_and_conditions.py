# app/schemas/terms_and_conditions.py
from typing import Optional, Annotated
from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from app.schemas.object_id import PyObjectId

Idx = Annotated[int, Field(ge=0, le=1_000_000, description="Display order; non-negative")]
Desc = Annotated[str, Field(min_length=1, max_length=10_000, description="Content of the terms")]


class TermsAndConditionsBase(BaseModel):
    idx: Idx
    description: Desc

    @field_validator("description", mode="before")
    @classmethod
    def _trim_description(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("description must not be empty.")
        return v

    model_config = {"extra": "ignore"}


class TermsAndConditionsCreate(TermsAndConditionsBase):
    pass


class TermsAndConditionsUpdate(BaseModel):
    idx: Optional[Idx] = None
    description: Optional[Desc] = None

    @field_validator("description", mode="before")
    @classmethod
    def _trim_description(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("description must not be empty when provided.")
        return v

    model_config = {"extra": "ignore"}


class TermsAndConditionsOut(TermsAndConditionsBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }