from __future__ import annotations
from typing import Dict

from fastapi import HTTPException

from app.schemas.object_id import PyObjectId
from app.schemas.card_details import CardDetailsOut
from app.crud import card_details as crud
from app.crud import payments as payments_crud  # to verify ownership via payments

async def get_my_card_details_by_payment_service(
    payment_id: PyObjectId,
    current_user: Dict,
) -> CardDetailsOut:
    # Verify the payment belongs to the user
    pay = await payments_crud.get_one(payment_id)
    if not pay:
        raise HTTPException(status_code=404, detail="Payment not found")
    if str(pay.user_id) != str(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="Forbidden")

    item = await crud.get_by_payment_id(payment_id)
    if not item:
        raise HTTPException(status_code=404, detail="Card details not found")
    return item

async def get_card_details_by_payment_admin_service(payment_id: PyObjectId) -> CardDetailsOut:
    item = await crud.get_by_payment_id(payment_id)
    if not item:
        raise HTTPException(status_code=404, detail="Card details not found")
    return item