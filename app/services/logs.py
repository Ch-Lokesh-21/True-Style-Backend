from sqlalchemy.ext.asyncio import AsyncSession
from app.crud import logs as crud
from app.schemas.logs import LoginLogCreate, LogoutLogCreate, RegisterLogCreate
import uuid

# CREATE
async def create_login_log(session: AsyncSession, payload: LoginLogCreate):
    return await crud.create_login_log(session, payload)

async def create_logout_log(session: AsyncSession, payload: LogoutLogCreate):
    return await crud.create_logout_log(session, payload)

async def create_register_log(session: AsyncSession, payload: RegisterLogCreate):
    return await crud.create_register_log(session, payload)

# LIST
async def list_login_logs(session: AsyncSession, limit: int = 100, offset: int = 0):
    return await crud.list_login_logs(session, limit, offset)

async def list_logout_logs(session: AsyncSession, limit: int = 100, offset: int = 0):
    return await crud.list_logout_logs(session, limit, offset)

async def list_register_logs(session: AsyncSession, limit: int = 100, offset: int = 0):
    return await crud.list_register_logs(session, limit, offset)

# DELETE
async def delete_login_log(session: AsyncSession, log_id: uuid.UUID):
    return await crud.delete_login_log(session, log_id)

async def delete_logout_log(session: AsyncSession, log_id: uuid.UUID):
    return await crud.delete_logout_log(session, log_id)

async def delete_register_log(session: AsyncSession, log_id: uuid.UUID):
    return await crud.delete_register_log(session, log_id)