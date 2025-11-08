# app/schemas/user_roles.py
from __future__ import annotations
from datetime import datetime
from typing import Optional, Annotated

from pydantic import BaseModel, Field, field_validator
from app.schemas.object_id import PyObjectId

RoleName = Annotated[str, Field(min_length=1, max_length=120, description="Role name")]

class UserRolesBase(BaseModel):
    role: RoleName

    @field_validator("role", mode="before")
    @classmethod
    def _trim_role(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("role must not be empty.")
        return v

    model_config = {"extra": "ignore"}

class UserRolesCreate(UserRolesBase):
    pass

class UserRolesUpdate(BaseModel):
    role: Optional[RoleName] = None

    @field_validator("role", mode="before")
    @classmethod
    def _trim_role(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("role must not be empty when provided.")
        return v

    model_config = {"extra": "ignore"}

class UserRolesOut(UserRolesBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,          # _id <-> id aliasing
        "from_attributes": False,          # validate Mongo dicts
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }