from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.models.contact_us import ContactUs
from app.schemas.contact_us import ContactUsCreate, ContactUsUpdate
import uuid

async def create_contact(session: AsyncSession, payload: ContactUsCreate) -> ContactUs:
    obj = ContactUs(**payload.dict())
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj

async def get_contact(session: AsyncSession, contact_id: uuid.UUID) -> Optional[ContactUs]:
    return await session.get(ContactUs, contact_id)

async def list_contacts(session: AsyncSession, limit: int = 100, offset: int = 0) -> List[ContactUs]:
    q = await session.execute(select(ContactUs).order_by(ContactUs.created_at.desc()).limit(limit).offset(offset))
    return q.scalars().all()

async def update_contact(session: AsyncSession, contact_id: uuid.UUID, payload: ContactUsUpdate) -> Optional[ContactUs]:
    db_obj = await session.get(ContactUs, contact_id)
    if not db_obj:
        return None
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(db_obj, field, value)
    session.add(db_obj)
    await session.commit()
    await session.refresh(db_obj)
    return db_obj

async def delete_contact(session: AsyncSession, contact_id: uuid.UUID) -> bool:
    db_obj = await session.get(ContactUs, contact_id)
    if not db_obj:
        return False
    await session.delete(db_obj)
    await session.commit()
    return True