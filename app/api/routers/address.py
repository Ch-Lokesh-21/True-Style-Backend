"""
Address Router

This module exposes API endpoints to fetch location details based on a pincode.
All endpoints require authentication and fetch data through the address service layer.
"""

from fastapi import APIRouter, Depends
from typing import Dict

from app.api.deps import get_current_user
from app.services.address import get_location_service

router = APIRouter()


@router.get("/{pincode}", dependencies=[Depends(get_current_user)])
async def get_location(pincode: int) -> Dict:
    """
    Get location details for a given pincode.

    Args:
        pincode (int): The pincode to lookup.

    Returns:
        Dict: Location details returned by the service.
    """
    return await get_location_service(pincode)