from sqlalchemy.ext.asyncio import AsyncSession
from app.crud import contact_us as crud
from app.schemas.contact_us import ContactUsCreate, ContactUsUpdate
import uuid


async def create_contact(session: AsyncSession, payload: ContactUsCreate):
    """
    Create a new contact-us entry.

    Args:
        session (AsyncSession): Active database session.
        payload (ContactUsCreate): Incoming validated request data.

    Returns:
        ContactUsRead: Newly created contact record.
    """
    return await crud.create_contact(session, payload)


async def get_contact(session: AsyncSession, contact_id: uuid.UUID):
    """
    Fetch a contact-us record by its UUID.

    Args:
        session (AsyncSession): Active database session.
        contact_id (UUID): Contact record ID.

    Returns:
        ContactUsRead | None: Contact-us record if found, else None.
    """
    return await crud.get_contact(session, contact_id)


async def list_contacts(session: AsyncSession, limit: int = 100, offset: int = 0):
    """
    List contact-us records with pagination.

    Args:
        session (AsyncSession): Active database session.
        limit (int): Maximum number of records to return.
        offset (int): Pagination offset.

    Returns:
        List[ContactUsRead]: Paginated list of records.
    """
    return await crud.list_contacts(session, limit, offset)


async def update_contact(session: AsyncSession, contact_id: uuid.UUID, payload: ContactUsUpdate):
    """
    Update a contact-us record.

    Args:
        session (AsyncSession): Active database session.
        contact_id (UUID): Record to update.
        payload (ContactUsUpdate): Fields updated.

    Returns:
        ContactUsRead | None: Updated record if successful, else None.
    """
    return await crud.update_contact(session, contact_id, payload)


async def delete_contact(session: AsyncSession, contact_id: uuid.UUID):
    """
    Delete a contact-us record.

    Args:
        session (AsyncSession): Active database session.
        contact_id (UUID): Record to delete.

    Returns:
        bool: True if deleted, False if not found.
    """
    return await crud.delete_contact(session, contact_id)