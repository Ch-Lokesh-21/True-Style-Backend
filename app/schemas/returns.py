# app/schemas/returns.py
from typing import Optional, Annotated
from datetime import datetime

from pydantic import BaseModel, Field, AnyUrl, TypeAdapter, field_validator
from app.schemas.object_id import PyObjectId

Money = Annotated[float, Field(ge=0, description="Non-negative amount")]
ImageUrlStr = Annotated[str, Field(max_length=2048, description="Image URL as plain string")]

_URL = TypeAdapter(AnyUrl)  # validates http/https, localhost, ports


class ReturnsBase(BaseModel):
    order_id: PyObjectId
    product_id: PyObjectId
    return_status_id: PyObjectId
    user_id: PyObjectId
    reason: Optional[str] = None
    image_url: Optional[ImageUrlStr] = None
    quantity: int
    amount: Optional[Money] = None

    @field_validator("reason", mode="before")
    @classmethod
    def _normalize_reason(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v == "":
                # Treat empty string as invalid; send None to skip update
                raise ValueError("reason must not be empty when provided.")
        return v

    @field_validator("image_url", mode="before")
    @classmethod
    def _validate_image_url(cls, v):
        if v is None:
            return v
        return str(_URL.validate_python(v))

    model_config = {"extra": "ignore"}


class ReturnsCreate(ReturnsBase):
    pass


class ReturnsUpdate(BaseModel):
    return_status_id: Optional[PyObjectId] = None
    model_config = {"extra": "ignore"}


class ReturnsOut(ReturnsBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }