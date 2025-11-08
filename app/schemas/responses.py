from pydantic import BaseModel
from typing import Optional

class MessageOut(BaseModel):
    message: str

class TokenOut(BaseModel):
    access_token: str
    access_jti: str
    access_exp: int
    token_type: str = "bearer"

class TokenRotatedOut(TokenOut):
    rotated: bool = True

class LoginResponse(BaseModel):
    access_token: str
    access_jti: str
    access_exp: int
    payload: dict
    token_type: str = "bearer"
