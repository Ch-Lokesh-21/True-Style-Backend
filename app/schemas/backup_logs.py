# app/schemas/backup_logs.py
from typing import Optional, Annotated
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator
from app.schemas.object_id import PyObjectId

# ---- Enums ----
class BackupStatus(str, Enum):
    success = "success"
    pending = "pending"
    failed = "failed"

class BackupScope(str, Enum):
    full = "full"
    users = "users"
    products = "products"
    orders = "orders"
    content = "content"
    payments = "payments"
    returns = "returns"
    exchanges = "exchanges"

class BackupFrequency(str, Enum):
    once = "once"
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"

# ---- Reusable constrained types ----
SizeGB = Annotated[float, Field(ge=0, description="Backup size in GB (non-negative).")]
PathStr = Annotated[str, Field(min_length=1, max_length=4096, description="Filesystem or bucket path")]

class BackupLogsBase(BaseModel):
    status: Optional[BackupStatus] = None
    size: SizeGB
    scope: Optional[BackupScope] = None
    frequency: Optional[BackupFrequency] = None
    path: PathStr

    # NEW (all optional) — scheduling/execution timestamps
    scheduled_at: Optional[datetime] = Field(
        default=None, description="When this backup is planned to run"
    )
    started_at: Optional[datetime] = Field(
        default=None, description="When the backup actually started"
    )
    finished_at: Optional[datetime] = Field(
        default=None, description="When the backup finished"
    )

    @field_validator("path", mode="before")
    @classmethod
    def _trim_path(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("path must not be empty.")
        return v

    model_config = {"extra": "ignore"}

class BackupLogsCreate(BackupLogsBase):
    pass

class BackupLogsUpdate(BaseModel):
    status: Optional[BackupStatus] = None
    size: Optional[SizeGB] = None
    scope: Optional[BackupScope] = None
    frequency: Optional[BackupFrequency] = None
    path: Optional[PathStr] = None

    # NEW optional timestamps for partial updates
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    @field_validator("path", mode="before")
    @classmethod
    def _trim_path(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("path must not be empty when provided.")
        return v

    model_config = {"extra": "ignore"}

class BackupLogsOut(BackupLogsBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }