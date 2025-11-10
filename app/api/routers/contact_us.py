"""
Contact Us Routes

Provides endpoints for:
- Creating contact messages
- Listing all contact submissions (restricted)
- Fetching individual contact submissions (restricted)
- Deleting a contact submission (restricted)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.database import get_session
from app.schemas.contact_us import ContactUsCreate, ContactUsRead, ContactUsUpdate
from app.services import contact_us as service
from app.api.deps import require_permission

router = APIRouter()


@router.post("/", response_model=ContactUsRead, status_code=status.HTTP_201_CREATED)
async def create_contact(
    payload: ContactUsCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new contact-us entry.

    Args:
        payload (ContactUsCreate): User-submitted name, email, subject, message.
        session (AsyncSession): Database session.

    Returns:
        ContactUsRead: The created contact record.
    """
    return await service.create_contact(session, payload)


@router.get(
    "/",
    response_model=List[ContactUsRead],
    dependencies=[Depends(require_permission("contact_us", "Read"))],
)
async def list_contacts(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    """
    List all contact-us records (paginated).

    Permissions:
        contact_us → Read

    Args:
        limit (int): Maximum records to return.
        offset (int): Skip N records.
        session (AsyncSession): Database session.

    Returns:
        List[ContactUsRead]: Paginated list of contact submissions.
    """
    return await service.list_contacts(session, limit, offset)


@router.get(
    "/{contact_id}",
    response_model=ContactUsRead,
    dependencies=[Depends(require_permission("contact_us", "Read"))],
)
async def get_contact(
    contact_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """
    Retrieve a single contact record by ID.

    Permissions:
        contact_us → Read

    Args:
        contact_id (uuid.UUID): Unique identifier of contact record.
        session (AsyncSession): Database session.

    Raises:
        HTTPException: If contact not found.

    Returns:
        ContactUsRead: The contact record.
    """
    obj = await service.get_contact(session, contact_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Contact not found")
    return obj


@router.delete(
    "/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("contact_us", "Delete"))],
)
async def delete_contact(
    contact_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """
    Delete a contact record permanently.

    Permissions:
        contact_us → Delete

    Args:
        contact_id (uuid.UUID): ID of the record to delete.
        session (AsyncSession): Database session.

    Raises:
        HTTPException: If contact does not exist.

    Returns:
        204 No Content on successful delete.
    """
    ok = await service.delete_contact(session, contact_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Contact not found")