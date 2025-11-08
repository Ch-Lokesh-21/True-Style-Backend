from __future__ import annotations
from typing import Optional, Annotated
from pydantic import BaseModel, Field, EmailStr, HttpUrl, StringConstraints, field_validator
from bson import ObjectId
import re
# name should have only alphabetic characters, spaces 

NameStr = Annotated[str, StringConstraints(min_length=1, max_length=50, strip_whitespace=True, pattern=r"^[A-Za-z\s]+$")]
CountryCodeStr = Annotated[str, StringConstraints(pattern=r"^\+\d{1,3}$", strip_whitespace=True)]
PhoneNumberStr = Annotated[str, StringConstraints(pattern=r"^\d{4,14}$", strip_whitespace=True)]
OtpInt = Annotated[int, Field(ge=0, le=999_999, description="6-digit code between 000000–999999")]
PasswordStr = Annotated[str, StringConstraints(min_length=8, max_length=256)]

class LoginIn(BaseModel):
    email: EmailStr
    password: PasswordStr
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[@$!%*?&]", v):
            raise ValueError("Password must contain at least one special character (@$!%*?&)")
        return v
class RegisterIn(BaseModel):
    first_name: NameStr
    last_name: NameStr
    email: EmailStr
    country_code: CountryCodeStr
    phone_no: PhoneNumberStr
    password: PasswordStr

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[@$!%*?&]", v):
            raise ValueError("Password must contain at least one special character (@$!%*?&)")
        return v
    
class ChangePasswordIn(BaseModel):
    old_password: PasswordStr
    new_password: PasswordStr
    
    @field_validator("old_password")
    @classmethod
    def validate_old_password(cls, v: str) -> str:
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[@$!%*?&]", v):
            raise ValueError("Password must contain at least one special character (@$!%*?&)")
        return v
    
    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[@$!%*?&]", v):
            raise ValueError("Password must contain at least one special character (@$!%*?&)")
        return v

class ForgotPasswordRequestIn(BaseModel):
    email: EmailStr

class ForgotPasswordVerifyIn(BaseModel):
    email: EmailStr
    otp: int = Field(ge=0, le=999_999)
    new_password: PasswordStr
    
    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[@$!%*?&]", v):
            raise ValueError("Password must contain at least one special character (@$!%*?&)")
        return v