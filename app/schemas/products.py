from typing import Optional, Annotated
from datetime import datetime

from pydantic import BaseModel, Field, AnyUrl, TypeAdapter, field_validator
from app.schemas.object_id import PyObjectId

# ---- Reusable constrained types ----
Name = Annotated[str, Field(min_length=1, max_length=200, description="Product name")]
Description = Annotated[str, Field(min_length=1, max_length=4000, description="Product description")]
Color = Annotated[str, Field(min_length=1, max_length=50, description="Color name or code")]
UrlStr = Annotated[str, Field(max_length=2048, description="URL as plain string")]
Rating = Annotated[float, Field(ge=0, le=5, description="0–5 rating")]
Price = Annotated[float, Field(ge=0, description="Non-negative price")]
Quantity = Annotated[int, Field(ge=0, le=1_000_000, description="Available stock (non-negative)")]
HSN = Annotated[int, Field(ge=0, description="HSN code (non-negative)")]
GSTPct = Annotated[int, Field(ge=0, le=100, description="GST percentage (0–100)")]
Money = Annotated[float, Field(ge=0, description="Non-negative amount")]

_URL = TypeAdapter(AnyUrl)  # allows http/https, localhost, custom ports, etc.


class ProductsBase(BaseModel):
    brand_id: PyObjectId
    occasion_id: PyObjectId
    category_id: PyObjectId
    product_type_id: PyObjectId

    name: Name
    description: Description
    rating: Optional[Rating] = None

    price: Price
    hsn_code: HSN
    gst_percentage: GSTPct
    gst_amount: Money
    total_price: Money

    color: Color
    out_of_stock: bool
    thumbnail_url: UrlStr

    # NEW FIELD
    quantity: Quantity

    # ---- Normalizers & URL validation ----
    @field_validator("name", "description", "color", mode="before")
    @classmethod
    def _strip_text(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Field cannot be empty.")
        return v

    @field_validator("thumbnail_url", mode="before")
    @classmethod
    def _validate_url(cls, v):
        # Validate with AnyUrl then return as plain string for Mongo
        return str(_URL.validate_python(v))

    model_config = {"extra": "ignore"}


class ProductsCreate(ProductsBase):
    pass


class ProductsUpdate(BaseModel):
    brand_id: Optional[PyObjectId] = None
    occasion_id: Optional[PyObjectId] = None
    category_id: Optional[PyObjectId] = None
    product_type_id: Optional[PyObjectId] = None

    name: Optional[Name] = None
    description: Optional[Description] = None
    rating: Optional[Rating] = None

    price: Optional[Price] = None
    hsn_code: Optional[HSN] = None
    gst_percentage: Optional[GSTPct] = None
    gst_amount: Optional[Money] = None
    total_price: Optional[Money] = None

    color: Optional[Color] = None
    out_of_stock: Optional[bool] = None
    thumbnail_url: Optional[UrlStr] = None

    # NEW FIELD
    quantity: Optional[Quantity] = None

    @field_validator("name", "description", "color", mode="before")
    @classmethod
    def _strip_text(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Field cannot be empty when provided.")
        return v

    @field_validator("thumbnail_url", mode="before")
    @classmethod
    def _validate_url(cls, v):
        if v is None:
            return v
        return str(_URL.validate_python(v))

    model_config = {"extra": "ignore"}


class ProductsOut(ProductsBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }