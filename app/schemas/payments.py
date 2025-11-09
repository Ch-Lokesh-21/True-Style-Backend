# app/schemas/payments.py
from typing import Optional, Annotated
from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from app.schemas.object_id import PyObjectId

Money = Annotated[float, Field(ge=0, description="Non-negative amount")]
Invoice = Annotated[str, Field(min_length=1, max_length=120, description="Invoice number")]


class PaymentsBase(BaseModel):
    user_id: PyObjectId                 # FK -> users._id
    order_id: PyObjectId                # FK -> orders._id
    payment_types_id: PyObjectId        # FK-like lookup (int)
    payment_status_id: PyObjectId       # FK-like lookup (int)
    invoice_no: Invoice
    delivery_fee: Optional[Money] = None
    amount: Optional[Money] = None

    @field_validator("invoice_no", mode="before")
    @classmethod
    def _trim_invoice(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("invoice_no must not be empty.")
        return v

    model_config = {"extra": "ignore"}


class PaymentsCreate(PaymentsBase):
    pass


class PaymentsUpdate(BaseModel):
    payment_status_id: Optional[PyObjectId] = None

    model_config = {"extra": "ignore"}


class PaymentsOut(PaymentsBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }