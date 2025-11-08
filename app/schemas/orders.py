# app/schemas/orders.py
from typing import Optional, Annotated
from datetime import datetime

from pydantic import BaseModel, Field
from app.schemas.object_id import PyObjectId

Money = Annotated[float, Field(ge=0, description="Order total; non-negative")]
OTP = Annotated[int, Field(ge=0, le=999_999, description="Delivery OTP (e.g., 6 digits)")]

class OrdersBase(BaseModel):
    user_id: PyObjectId          
    address: dict       
    status_id: PyObjectId         
    total: Money
    delivery_otp: Optional[OTP] = None

    model_config = {"extra": "ignore"}

class OrdersCreate(OrdersBase):
    pass

class OrdersUpdate(BaseModel):
    user_id: Optional[PyObjectId] = None
    address_id: Optional[PyObjectId] = None
    status_id: Optional[PyObjectId] = None
    total: Optional[Money] = None
    delivery_otp: Optional[OTP] = None

    model_config = {"extra": "ignore"}

class OrdersOut(OrdersBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }
