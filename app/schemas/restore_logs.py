# app/schemas/restore_logs.py
from typing import Optional
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field
from app.schemas.object_id import PyObjectId

class RestoreStatus(str, Enum):
    success = "success"
    pending = "pending"
    failed = "failed"

class RestoreLogsBase(BaseModel):
    backup_id: PyObjectId                 # FK to backup_logs._id
    status: Optional[RestoreStatus] = None
    model_config = {"extra": "ignore"}

class RestoreLogsCreate(RestoreLogsBase):
    pass

class RestoreLogsUpdate(BaseModel):
    backup_id: Optional[PyObjectId] = None
    status: Optional[RestoreStatus] = None
    reason: Optional[str] = None

    model_config = {"extra": "ignore"}

class RestoreLogsOut(RestoreLogsBase):
    id: PyObjectId = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

    model_config = {
        "populate_by_name": True,
        "from_attributes": False,
        "json_encoders": {PyObjectId: str},
        "extra": "ignore",
    }
