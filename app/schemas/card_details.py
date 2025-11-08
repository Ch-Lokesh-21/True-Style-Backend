# app/schemas/card_details.py
from typing import Optional
from pydantic import BaseModel, Field, constr
from datetime import datetime
from app.schemas.object_id import PyObjectId

class CardDetailsBase(BaseModel):
    name: str

class CardDetailsCreate(CardDetailsBase):
    card_no: str

class CardDetailsUpdate(BaseModel):
    name: Optional[str] = None

class CardDetailsOut(CardDetailsBase):
    card_no: str
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }