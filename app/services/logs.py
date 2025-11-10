from sqlalchemy.ext.asyncio import AsyncSession
from app.crud import logs as crud
from app.schemas.logs import LoginLogCreate, LogoutLogCreate, RegisterLogCreate
import uuid


# ----------------------------------------------------------
# CREATE
# ----------------------------------------------------------

async def create_login_log(session: AsyncSession, payload: LoginLogCreate):
    """
    Create a new login log entry.

    Args:
        session (AsyncSession): SQLAlchemy session.
        payload (LoginLogCreate): Login request details.

    Returns:
        LoginLogRead: Created log record.
    """
    return await crud.create_login_log(session, payload)


async def create_logout_log(session: AsyncSession, payload: LogoutLogCreate):
    """
    Create a new logout log entry.

    Args:
        session (AsyncSession): SQLAlchemy session.
        payload (LogoutLogCreate): Logout request details.

    Returns:
        LogoutLogRead: Created log record.
    """
    return await crud.create_logout_log(session, payload)


async def create_register_log(session: AsyncSession, payload: RegisterLogCreate):
    """
    Create a new register log entry.

    Args:
        session (AsyncSession): SQLAlchemy session.
        payload (RegisterLogCreate): Registration request details.

    Returns:
        RegisterLogRead: Created log record.
    """
    return await crud.create_register_log(session, payload)


# ----------------------------------------------------------
# LIST
# ----------------------------------------------------------

async def list_login_logs(session: AsyncSession, limit: int = 100, offset: int = 0):
    """
    Fetch paginated login logs.

    Args:
        session (AsyncSession): SQLAlchemy session.
        limit (int): Maximum number of results.
        offset (int): Number of records to skip.

    Returns:
        List[LoginLogRead]: List of login log entries.
    """
    return await crud.list_login_logs(session, limit, offset)


async def list_logout_logs(session: AsyncSession, limit: int = 100, offset: int = 0):
    """
    Fetch paginated logout logs.

    Args:
        session (AsyncSession): SQLAlchemy session.
        limit (int): Maximum number of results.
        offset (int): Number of records to skip.

    Returns:
        List[LogoutLogRead]: List of logout log entries.
    """
    return await crud.list_logout_logs(session, limit, offset)


async def list_register_logs(session: AsyncSession, limit: int = 100, offset: int = 0):
    """
    Fetch paginated register logs.

    Args:
        session (AsyncSession): SQLAlchemy session.
        limit (int): Maximum number of results.
        offset (int): Number of records to skip.

    Returns:
        List[RegisterLogRead]: List of register log entries.
    """
    return await crud.list_register_logs(session, limit, offset)


# ----------------------------------------------------------
# DELETE
# ----------------------------------------------------------

async def delete_login_log(session: AsyncSession, log_id: uuid.UUID):
    """
    Delete a login log entry by ID.

    Args:
        session (AsyncSession): SQLAlchemy session.
        log_id (uuid.UUID): Log record identifier.

    Returns:
        bool: True if deleted, False otherwise.
    """
    return await crud.delete_login_log(session, log_id)


async def delete_logout_log(session: AsyncSession, log_id: uuid.UUID):
    """
    Delete a logout log entry by ID.

    Args:
        session (AsyncSession): SQLAlchemy session.
        log_id (uuid.UUID): Log record identifier.

    Returns:
        bool: True if deleted, False otherwise.
    """
    return await crud.delete_logout_log(session, log_id)


async def delete_register_log(session: AsyncSession, log_id: uuid.UUID):
    """
    Delete a register log entry by ID.

    Args:
        session (AsyncSession): SQLAlchemy session.
        log_id (uuid.UUID): Log record identifier.

    Returns:
        bool: True if deleted, False otherwise.
    """
    return await crud.delete_register_log(session, log_id)