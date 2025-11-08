# app/schemas/payment_types.py
from typing import Optional, Annotated
from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from app.schemas.object_id import PyObjectId

TypeText = Annotated[str, Field(min_length=1, max_length=120, description="Payment type label")]


class PaymentTypesBase(BaseModel):
    type: TypeText

    @field_validator("type", mode="before")
    @classmethod
    def _normalize_type(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("type must not be empty.")
        return v

    model_config = {"extra": "ignore"}


class PaymentTypesCreate(PaymentTypesBase):
    pass


class PaymentTypesUpdate(BaseModel):
    type: Optional[TypeText] = None

    @field_validator("type", mode="before")
    @classmethod
    def _normalize_type(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("type must not be empty when provided.")
        return v

    model_config = {"extra": "ignore"}


class PaymentTypesOut(PaymentTypesBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }