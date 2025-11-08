from __future__ import annotations
from typing import Optional, Annotated
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, StringConstraints, field_validator, ConfigDict
from bson import ObjectId
from app.schemas.object_id import PyObjectId

# ---------------------- Constrained types ----------------------
NameStr = Annotated[str, StringConstraints(min_length=1, max_length=50, strip_whitespace=True, pattern=r"^[A-Za-z\s]+$")]
CountryCodeStr = Annotated[str, StringConstraints(pattern=r"^\+\d{1,3}$", strip_whitespace=True)]
PhoneNumberStr = Annotated[str, StringConstraints(pattern=r"^\d{4,14}$", strip_whitespace=True)]
OtpInt = Annotated[int, Field(ge=0, le=999_999, description="6-digit code between 000000–999999")]

# ---------------------- Base Model ----------------------
class UserBase(BaseModel):
    user_status_id: PyObjectId
    role_id: PyObjectId
    first_name: NameStr
    last_name: NameStr
    email: EmailStr
    country_code: CountryCodeStr
    phone_no: PhoneNumberStr
    profile_img_url: Optional[str] = None
    otp: Optional[OtpInt] = None
    last_login: Optional[datetime] = None

    @field_validator("role_id")
    @classmethod
    def role_id_is_objectid(cls, v: str) -> str:
        if not ObjectId.is_valid(v):
            raise ValueError("role_id must be a valid Mongo ObjectId string.")
        return v

# ---------------------- Create / Update / Output ----------------------
class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    user_status_id: Optional[PyObjectId]=None
    first_name: Optional[NameStr] = None
    last_name: Optional[NameStr] = None
    email: Optional[EmailStr] = None
    country_code: Optional[CountryCodeStr] = None
    phone_no: Optional[PhoneNumberStr] = None
    profile_img_url: Optional[str] = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: Optional[EmailStr]) -> Optional[EmailStr]:
        return EmailStr(str(v).lower()) if v else None

class UserOut(BaseModel):
    id: PyObjectId = Field(alias="_id")
    user_status_id: PyObjectId
    role_id: PyObjectId
    first_name: NameStr
    last_name: NameStr
    email: EmailStr
    country_code: CountryCodeStr
    phone_no: PhoneNumberStr
    profile_img_url: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=False,
        extra="ignore",
        json_encoders={PyObjectId: str},
    )