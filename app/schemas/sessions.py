from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

class SessionCreate(BaseModel):
    user_id: str
    jti: str
    refresh_hash: str
    exp: datetime
    family_id: Optional[str] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None

class SessionOut(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    jti: str
    exp: datetime
    revokedAt: Optional[datetime] = None
    createdAt: datetime
    updatedAt: datetime

class SessionUpdate(BaseModel):
    revokedAt: Optional[datetime] = None
