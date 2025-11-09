from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.schemas.contact_us import ContactUsCreate, ContactUsRead, ContactUsUpdate
from app.services import contact_us as service
import uuid
from app.api.deps import require_permission
router = APIRouter()

@router.post("/", response_model=ContactUsRead, status_code=status.HTTP_201_CREATED)
async def create_contact(payload: ContactUsCreate, session: AsyncSession = Depends(get_session)):
    return await service.create_contact(session, payload)

@router.get("/", response_model=List[ContactUsRead], dependencies=[Depends(require_permission("contact_us","Read"))])
async def list_contacts(limit: int = Query(50, ge=1, le=1000), offset: int = 0, session: AsyncSession = Depends(get_session)):
    return await service.list_contacts(session, limit, offset)

@router.get("/{contact_id}", response_model=ContactUsRead, dependencies=[Depends(require_permission("contact_us","Read"))])
async def get_contact(contact_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    obj = await service.get_contact(session, contact_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Contact not found")
    return obj

@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("contact_us","Delete"))])
async def delete_contact(contact_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    ok = await service.delete_contact(session, contact_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Contact not found")