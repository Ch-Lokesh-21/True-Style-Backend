# app/schemas/exchange_status.py
from typing import Optional, Annotated
from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from app.schemas.object_id import PyObjectId

StatusText = Annotated[str, Field(min_length=1, max_length=120, description="Status label")]


class ExchangeStatusBase(BaseModel):
    status: StatusText

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_status(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("status must not be empty.")
        return v

    model_config = {"extra": "ignore"}


class ExchangeStatusCreate(ExchangeStatusBase):
    pass


class ExchangeStatusUpdate(BaseModel):
    status: Optional[StatusText] = None

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_status(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("status must not be empty when provided.")
        return v

    model_config = {"extra": "ignore"}


class ExchangeStatusOut(ExchangeStatusBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }