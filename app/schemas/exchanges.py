# app/schemas/exchanges.py
from typing import Optional, Annotated
from datetime import datetime

from pydantic import BaseModel, Field, AnyUrl, TypeAdapter, field_validator
from app.schemas.object_id import PyObjectId

Text = Annotated[str, Field(min_length=1, max_length=200, description="Non-empty text up to 200 chars")]
ImageUrlStr = Annotated[str, Field(max_length=2048, description="Image URL as plain string")]
Qnt = Annotated[int,Field(ge=0)]
_URL = TypeAdapter(AnyUrl)  # accepts http/https, localhost, ports


class ExchangesBase(BaseModel):
    order_id: PyObjectId
    product_id: PyObjectId
    exchange_status_id: PyObjectId
    user_id: PyObjectId
    reason: Optional[Text] = None
    image_url: Optional[ImageUrlStr] = None
    new_quantity: Optional[Qnt] = None
    new_size: Optional[Text] = None

    @field_validator("reason", "new_size", mode="before")
    @classmethod
    def _trim_text(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v == "":
                raise ValueError("Field must not be empty when provided.")
        return v

    @field_validator("image_url", mode="before")
    @classmethod
    def _validate_image_url(cls, v):
        if v is None:
            return v
        return str(_URL.validate_python(v))

    model_config = {"extra": "ignore"}


class ExchangesCreate(ExchangesBase):
    pass


class ExchangesUpdate(BaseModel):
    exchange_status_id: Optional[PyObjectId] = None


    model_config = {"extra": "ignore"}


class ExchangesOut(ExchangesBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }
