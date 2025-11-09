from sqlalchemy.ext.asyncio import AsyncSession
from app.crud import contact_us as crud
from app.schemas.contact_us import ContactUsCreate, ContactUsUpdate
import uuid

async def create_contact(session: AsyncSession, payload: ContactUsCreate):
    return await crud.create_contact(session, payload)

async def get_contact(session: AsyncSession, contact_id: uuid.UUID):
    return await crud.get_contact(session, contact_id)

async def list_contacts(session: AsyncSession, limit: int = 100, offset: int = 0):
    return await crud.list_contacts(session, limit, offset)

async def update_contact(session: AsyncSession, contact_id: uuid.UUID, payload: ContactUsUpdate):
    return await crud.update_contact(session, contact_id, payload)

async def delete_contact(session: AsyncSession, contact_id: uuid.UUID):
    return await crud.delete_contact(session, contact_id)