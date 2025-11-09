from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
import uuid

class ContactUsBase(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)

class ContactUsCreate(ContactUsBase):
    pass

class ContactUsUpdate(BaseModel):
    email: Optional[EmailStr]
    name: Optional[str]
    message: Optional[str]

class ContactUsRead(ContactUsBase):
    id: uuid.UUID
    created_at: Optional[datetime]

    class Config:
        from_attributes = True