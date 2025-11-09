# app/api/routes/card_details.py
from __future__ import annotations
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_permission, get_current_user
from app.schemas.object_id import PyObjectId
from app.schemas.card_details import CardDetailsOut
from app.crud import card_details as crud
from app.crud import payments as payments_crud  # to verify ownership via payments

router = APIRouter()  # mounted at /card-details


# ---------- USER: read my card details by payment_id ----------
@router.get(
    "/my/by-payment/{payment_id}",
    response_model=CardDetailsOut,
    dependencies=[Depends(require_permission("card_details", "Read"))],
)
async def get_my_card_details_by_payment(
    payment_id: PyObjectId,
    current_user: Dict = Depends(get_current_user),
):
    """
    Return masked card details for a payment **owned by the current user**.
    """
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


# ---------- ADMIN: read card details by any payment_id ----------
@router.get(
    "/by-payment/{payment_id}",
    response_model=CardDetailsOut,
    dependencies=[Depends(require_permission("card_details", "Read", "admin"))],
)
async def get_card_details_by_payment_admin(payment_id: PyObjectId):
    """
    Admin can fetch masked card details for any `payment_id`.
    (Masked even for admins to avoid PAN exposure via API.)
    """
    item = await crud.get_by_payment_id(payment_id)
    if not item:
        raise HTTPException(status_code=404, detail="Card details not found")
    return item