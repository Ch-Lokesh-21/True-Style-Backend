from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from typing import List
import uuid

from app.models.login_logs import LoginLogs
from app.models.register_logs import RegisterLogs
from app.models.logout_logs import LogoutLogs
from app.schemas.logs import LoginLogCreate, LogoutLogCreate, RegisterLogCreate


# --------- CREATE ---------
async def create_login_log(session: AsyncSession, payload: LoginLogCreate) -> LoginLogs:
    obj = LoginLogs(**payload.model_dump())
    print(obj)
    print("hello")
    session.add(obj)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    await session.refresh(obj)
    return obj


async def create_logout_log(session: AsyncSession, payload: LogoutLogCreate) -> LogoutLogs:
    data = payload.model_dump(mode="python", exclude_unset=True)
    obj = LogoutLogs(**data)
    session.add(obj)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    await session.refresh(obj)
    return obj


async def create_register_log(session: AsyncSession, payload: RegisterLogCreate) -> RegisterLogs:
    data = payload.model_dump(mode="python", exclude_unset=True)
    obj = RegisterLogs(**data)
    session.add(obj)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    await session.refresh(obj)
    return obj


# --------- LIST ---------
async def list_login_logs(session: AsyncSession, limit: int = 100, offset: int = 0) -> List[LoginLogs]:
    result = await session.execute(
        select(LoginLogs).order_by(LoginLogs.created_at.desc()).limit(limit).offset(offset)
    )
    return result.scalars().all()


async def list_logout_logs(session: AsyncSession, limit: int = 100, offset: int = 0) -> List[LogoutLogs]:
    result = await session.execute(
        select(LogoutLogs).order_by(LogoutLogs.created_at.desc()).limit(limit).offset(offset)
    )
    return result.scalars().all()


async def list_register_logs(session: AsyncSession, limit: int = 100, offset: int = 0) -> List[RegisterLogs]:
    result = await session.execute(
        select(RegisterLogs).order_by(RegisterLogs.created_at.desc()).limit(limit).offset(offset)
    )
    return result.scalars().all()


# --------- DELETE ---------
async def delete_login_log(session: AsyncSession, log_id: uuid.UUID) -> bool:
    obj = await session.get(LoginLogs, log_id)
    if not obj:
        return False
    await session.delete(obj)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    return True


async def delete_logout_log(session: AsyncSession, log_id: uuid.UUID) -> bool:
    obj = await session.get(LogoutLogs, log_id)
    if not obj:
        return False
    await session.delete(obj)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    return True


async def delete_register_log(session: AsyncSession, log_id: uuid.UUID) -> bool:
    obj = await session.get(RegisterLogs, log_id)
    if not obj:
        return False
    await session.delete(obj)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    return True