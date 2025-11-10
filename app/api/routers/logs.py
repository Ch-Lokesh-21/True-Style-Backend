"""
Login / Logout / Register Logs API

Provides audit logging endpoints for user authentication events.
All logs are stored in PostgreSQL via SQLAlchemy AsyncSession.
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.schemas.logs import (
    LoginLogCreate, LoginLogRead,
    LogoutLogCreate, LogoutLogRead,
    RegisterLogCreate, RegisterLogRead
)
from app.services import logs as service
import uuid
from app.api.deps import require_permission

router = APIRouter()

# --------------------------------------------------------
# LOGIN LOGS
# --------------------------------------------------------

@router.post(
    "/login",
    response_model=LoginLogRead,
    dependencies=[Depends(require_permission("login_logs","Create"))]
)
async def create_login_log(
    payload: LoginLogCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new login audit log.

    Args:
        payload (LoginLogCreate): Information containing user_id, IP, user-agent, etc.
        session (AsyncSession): Database session dependency.

    Returns:
        LoginLogRead: The stored login log entry.
    """
    return await service.create_login_log(session, payload)


@router.get(
    "/login",
    response_model=List[LoginLogRead],
    dependencies=[Depends(require_permission("login_logs","Read"))]
)
async def list_login_logs(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    """
    List stored login logs, paginated.

    Args:
        limit (int): Maximum number of records per page.
        offset (int): Record offset for pagination.

    Returns:
        List[LoginLogRead]: List of login log entries.
    """
    return await service.list_login_logs(session, limit, offset)


@router.delete(
    "/login/{log_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("login_logs","Delete"))]
)
async def delete_login_log(
    log_id: uuid.UUID,
    session: AsyncSession = Depends(get_session)
):
    """
    Delete a specific login log by UUID.

    Raises:
        HTTPException 404: When the log does not exist.
    """
    ok = await service.delete_login_log(session, log_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Login log not found")


# --------------------------------------------------------
# LOGOUT LOGS
# --------------------------------------------------------

@router.post(
    "/logout",
    response_model=LogoutLogRead,
    dependencies=[Depends(require_permission("logout_logs","Create"))]
)
async def create_logout_log(
    payload: LogoutLogCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    Create a logout audit log entry.

    Returns:
        LogoutLogRead: Stored logout log.
    """
    return await service.create_logout_log(session, payload)


@router.get(
    "/logout",
    response_model=List[LogoutLogRead],
    dependencies=[Depends(require_permission("logout_logs","Read"))]
)
async def list_logout_logs(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    """
    List logout logs with pagination.

    Returns:
        List[LogoutLogRead]: Log records.
    """
    return await service.list_logout_logs(session, limit, offset)


@router.delete(
    "/logout/{log_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("logout_logs","Delete"))]
)
async def delete_logout_log(
    log_id: uuid.UUID,
    session: AsyncSession = Depends(get_session)
):
    """
    Delete a logout log by UUID.

    Raises:
        HTTPException 404: If log does not exist.
    """
    ok = await service.delete_logout_log(session, log_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Logout log not found")


# --------------------------------------------------------
# REGISTER LOGS
# --------------------------------------------------------

@router.post(
    "/register",
    response_model=RegisterLogRead,
    dependencies=[Depends(require_permission("register_logs","Create"))]
)
async def create_register_log(
    payload: RegisterLogCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    Create a register audit log entry after a successful user registration.

    Returns:
        RegisterLogRead: Stored register log.
    """
    return await service.create_register_log(session, payload)


@router.get(
    "/register",
    response_model=List[RegisterLogRead],
    dependencies=[Depends(require_permission("register_logs","Read"))]
)
async def list_register_logs(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    """
    List registration logs with pagination.

    Returns:
        List[RegisterLogRead]: Log records.
    """
    return await service.list_register_logs(session, limit, offset)


@router.delete(
    "/register/{log_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("register_logs","Delete"))]
)
async def delete_register_log(
    log_id: uuid.UUID,
    session: AsyncSession = Depends(get_session)
):
    """
    Delete a registration log by UUID.

    Raises:
        HTTPException 404: If log does not exist.
    """
    ok = await service.delete_register_log(session, log_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Register log not found")