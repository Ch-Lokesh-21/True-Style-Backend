from pydantic import BaseModel
from datetime import datetime

class RevocationCreate(BaseModel):
    jti: str
    expiresAt: datetime
    reason: str

class RevocationOut(BaseModel):
    jti: str
    expiresAt: datetime
    reason: str
    createdAt: datetime
