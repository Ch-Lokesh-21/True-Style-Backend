from __future__ import annotations
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_permission, get_current_user
from app.schemas.object_id import PyObjectId
from app.schemas.card_details import CardDetailsOut
from app.services.card_details import (
    get_my_card_details_by_payment_service,
    get_card_details_by_payment_admin_service,
)

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
    return await get_my_card_details_by_payment_service(payment_id, current_user)

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
    return await get_card_details_by_payment_admin_service(payment_id)