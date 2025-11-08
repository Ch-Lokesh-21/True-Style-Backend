from typing import Optional, Annotated
from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from app.schemas.object_id import PyObjectId

CategoryName = Annotated[str, Field(min_length=1, max_length=120, description="Category name")]


class CategoriesBase(BaseModel):
    category: CategoryName

    @field_validator("category", mode="before")
    @classmethod
    def _normalize_category(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("category must not be empty.")
        return v

    model_config = {"extra": "ignore"}


class CategoriesCreate(CategoriesBase):
    pass


class CategoriesUpdate(BaseModel):
    category: Optional[CategoryName] = None

    @field_validator("category", mode="before")
    @classmethod
    def _normalize_category(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("category must not be empty when provided.")
        return v

    model_config = {"extra": "ignore"}


class CategoriesOut(CategoriesBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }