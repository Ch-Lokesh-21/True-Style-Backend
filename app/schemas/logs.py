from pydantic import BaseModel, EmailStr
from datetime import datetime
import uuid


class LogBase(BaseModel):
    user_id: str
    first_name: str
    last_name: str
    email: EmailStr


class LogRead(LogBase):
    id: uuid.UUID
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


class LoginLogCreate(LogBase):
    pass


class LogoutLogCreate(LogBase):
    pass


class RegisterLogCreate(LogBase):
    pass


class LoginLogRead(LogRead):
    pass


class LogoutLogRead(LogRead):
    pass


class RegisterLogRead(LogRead):
    pass