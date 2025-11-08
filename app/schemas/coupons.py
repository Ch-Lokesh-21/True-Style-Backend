# app/schemas/coupons.py
from typing import Optional, Annotated
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator
from app.schemas.object_id import PyObjectId

# -----------------------------
# ENUMS
# -----------------------------

class CouponType(str, Enum):
    percent = "percent"
    flat = "flat"

# -----------------------------
# Reusable Constrained Types
# -----------------------------

NonNegInt = Annotated[int, Field(ge=0, description="Must be non-negative.")]
NonNegAmount = Annotated[int, Field(ge=0, description="Amount must be non-negative.")]
CodeStr = Annotated[str, Field(min_length=1, max_length=120)]

# -----------------------------
# Main Models
# -----------------------------

class CouponsBase(BaseModel):
    coupons_status_id: PyObjectId
    code: CodeStr
    discount: NonNegInt
    minimum_price: NonNegInt
    usage: NonNegInt
    type: CouponType

    @field_validator("code", mode="before")
    @classmethod
    def _trim_code(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("code must not be empty when provided.")
        return v

    model_config = {"extra": "ignore"}


class CouponsCreate(CouponsBase):
    pass


class CouponsUpdate(BaseModel):
    coupons_status_id: Optional[PyObjectId] = None
    code: Optional[CodeStr] = None
    discount: Optional[NonNegInt] = None
    minimum_price: Optional[NonNegInt] = None
    usage: Optional[NonNegInt] = None
    type: Optional[CouponType] = None

    @field_validator("code", mode="before")
    @classmethod
    def _trim_code(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("code must not be empty when provided.")
        return v

    model_config = {"extra": "ignore"}


class CouponsOut(CouponsBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }

# ----------------------------------------------
# Validation I/O Models for Coupon Checking Logic
# ----------------------------------------------

class CouponCheckIn(BaseModel):
    code: str
    amount: float  # original cart amount before discount

    @field_validator("code", mode="before")
    @classmethod
    def _trim_code(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("code must not be empty.")
        return v


class CouponCheckOut(BaseModel):
    code: str
    valid: bool
    discount_type: Optional[str] = None       # "percent" | "flat" | None
    discount_value: Optional[int] = None      # the coupon's discount field
    discount_amount: float                    # computed deduction
    final_amount: float                       # amount - discount_amount
    reason: Optional[str] = None              # explanation if invalid

    model_config = {"extra": "ignore"}