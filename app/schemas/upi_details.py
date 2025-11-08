# app/schemas/upi_details.py
from typing import Optional, Annotated
from datetime import datetime
import re

from pydantic import BaseModel, Field, field_validator
from app.schemas.object_id import PyObjectId

# UPI format: name@bank
_UPI_RE = re.compile(r"^[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{2,}$")

UpiStr = Annotated[str, Field(min_length=3, max_length=120, description="Valid UPI ID")]


class UpiDetailsBase(BaseModel):
    payment_id: PyObjectId        # FK -> payments._id
    upi_id: UpiStr                # stored directly

    @field_validator("upi_id", mode="before")
    @classmethod
    def _normalize_upi(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("upi_id must not be empty.")
            if not _UPI_RE.fullmatch(v):
                raise ValueError("Invalid UPI format. Expected something@bank, e.g., name@okicici")
        return v

    model_config = {"extra": "ignore"}


class UpiDetailsCreate(UpiDetailsBase):
    pass


class UpiDetailsUpdate(BaseModel):
    payment_id: Optional[PyObjectId] = None
    upi_id: Optional[UpiStr] = None

    @field_validator("upi_id", mode="before")
    @classmethod
    def _normalize_upi(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("upi_id must not be empty when provided.")
            if not _UPI_RE.fullmatch(v):
                raise ValueError("Invalid UPI format. Expected something@bank, e.g., user@upi")
        return v

    model_config = {"extra": "ignore"}


class UpiDetailsOut(UpiDetailsBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }