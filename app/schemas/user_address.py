# app/schemas/user_address.py
from __future__ import annotations
from typing import Optional, Annotated
from datetime import datetime
import re

from pydantic import BaseModel, Field, field_validator
from app.schemas.object_id import PyObjectId

# ---- Constrained types ----
MobileStr = Annotated[str, Field(min_length=10, max_length=10, description="10-digit mobile number")]
PinCode   = Annotated[int, Field(ge=100000, le=999999, description="Indian 6-digit PIN")]
Text120   = Annotated[str, Field(min_length=1, max_length=120)]
AddrStr   = Annotated[str, Field(min_length=1, max_length=400)]

_MOBILE_RE = re.compile(r"^[6-9]\d{9}$")

class UserAddressBase(BaseModel):
    user_id: PyObjectId
    mobile_no: MobileStr
    postal_code: PinCode
    country: Text120
    state: Text120
    city: Text120
    address: AddrStr

    @field_validator("country", "state", "city", "address", mode="before")
    @classmethod
    def _trim_text(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Field must not be empty.")
        return v

    @field_validator("mobile_no", mode="before")
    @classmethod
    def _validate_mobile(cls, v: str):
        if isinstance(v, str):
            s = re.sub(r"\s+", "", v)  # remove spaces if any
            if not _MOBILE_RE.fullmatch(s):
                raise ValueError("mobile_no must be a valid 10-digit Indian mobile (starts 6–9).")
            return s
        return v

    model_config = {"extra": "ignore"}


class UserAddressCreate(UserAddressBase):
    pass


class UserAddressUpdate(BaseModel):
    mobile_no: Optional[MobileStr] = None
    postal_code: Optional[PinCode] = None
    country: Optional[Text120] = None
    state: Optional[Text120] = None
    city: Optional[Text120] = None
    address: Optional[AddrStr] = None

    @field_validator("country", "state", "city", "address", mode="before")
    @classmethod
    def _trim_text(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Field must not be empty when provided.")
        return v

    @field_validator("mobile_no", mode="before")
    @classmethod
    def _validate_mobile(cls, v: Optional[str]):
        if v is None:
            return v
        s = re.sub(r"\s+", "", v)
        if not _MOBILE_RE.fullmatch(s):
            raise ValueError("mobile_no must be a valid 10-digit Indian mobile (starts 6–9).")
        return s

    model_config = {"extra": "ignore"}


class UserAddressOut(UserAddressBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,          # _id <-> id aliasing
        "from_attributes": False,          # validate raw Mongo dicts
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }