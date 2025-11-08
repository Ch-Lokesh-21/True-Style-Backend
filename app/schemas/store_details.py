# app/schemas/store_details.py
from typing import Optional, Annotated
from datetime import datetime
import re

from pydantic import BaseModel, Field, field_validator
from app.schemas.object_id import PyObjectId

# -------- Constrained types --------
NameStr     = Annotated[str, Field(min_length=1, max_length=200)]
PANStr      = Annotated[str, Field(min_length=10, max_length=10, description="PAN: AAAAA9999A")]
GSTStr      = Annotated[str, Field(min_length=15, max_length=15, description="GSTIN: 22AAAAA9999A1Z5")]
AddrStr     = Annotated[str, Field(min_length=1, max_length=400)]
CountryStr  = Annotated[str, Field(min_length=1, max_length=120)]
StateStr    = Annotated[str, Field(min_length=1, max_length=120)]
CityStr     = Annotated[str, Field(min_length=1, max_length=120)]
PinCode     = Annotated[int, Field(ge=100000, le=999999, description="Indian 6-digit PIN")]

_PAN_RE = re.compile(r"^[A-Z]{5}\d{4}[A-Z]$")
# GSTIN: 2 digits (state) + PAN (10) + entity code (1) + 'Z' + checksum (1)
_GST_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][0-9A-Z]Z[0-9A-Z]$")

def _clean_upper_alnum(s: str) -> str:
    # remove spaces/dashes/underscores, uppercase
    return re.sub(r"[\s\-_]", "", s).upper()

class StoreDetailsBase(BaseModel):
    name: NameStr
    pan_no: PANStr
    gst_no: GSTStr
    address: AddrStr
    postal_code: PinCode
    country: CountryStr
    state: StateStr
    city: CityStr

    # ---- Normalizers / validators ----
    @field_validator("name", "address", "country", "state", "city", mode="before")
    @classmethod
    def _trim_nonempty(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Field must not be empty.")
        return v

    @field_validator("pan_no", mode="before")
    @classmethod
    def _validate_pan(cls, v: str):
        if v is None:
            return v
        s = _clean_upper_alnum(v)
        if not _PAN_RE.fullmatch(s):
            raise ValueError("Invalid PAN format. Expected AAAAA9999A.")
        return s

    @field_validator("gst_no", mode="before")
    @classmethod
    def _validate_gst(cls, v: str):
        if v is None:
            return v
        s = _clean_upper_alnum(v)
        if not _GST_RE.fullmatch(s):
            raise ValueError("Invalid GSTIN format. Expected 22AAAAA9999A1Z5 pattern.")
        return s

    model_config = {"extra": "ignore"}


class StoreDetailsCreate(StoreDetailsBase):
    pass


class StoreDetailsUpdate(BaseModel):
    name: Optional[NameStr] = None
    pan_no: Optional[PANStr] = None
    gst_no: Optional[GSTStr] = None
    address: Optional[AddrStr] = None
    postal_code: Optional[PinCode] = None
    country: Optional[CountryStr] = None
    state: Optional[StateStr] = None
    city: Optional[CityStr] = None

    @field_validator("name", "address", "country", "state", "city", mode="before")
    @classmethod
    def _trim_nonempty(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Field must not be empty when provided.")
        return v

    @field_validator("pan_no", mode="before")
    @classmethod
    def _validate_pan(cls, v: Optional[str]):
        if v is None:
            return v
        s = _clean_upper_alnum(v)
        if not _PAN_RE.fullmatch(s):
            raise ValueError("Invalid PAN format. Expected AAAAA9999A.")
        return s

    @field_validator("gst_no", mode="before")
    @classmethod
    def _validate_gst(cls, v: Optional[str]):
        if v is None:
            return v
        s = _clean_upper_alnum(v)
        if not _GST_RE.fullmatch(s):
            raise ValueError("Invalid GSTIN format. Expected 22AAAAA9999A1Z5 pattern.")
        return s

    model_config = {"extra": "ignore"}


class StoreDetailsOut(StoreDetailsBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }