"""
Users API Routes

Provides:
- Profile read & update for logged-in users
- Admin: create users, list, update status, delete users
- Image upload handled via Form/File for profile updates
"""

from __future__ import annotations
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, Query, status, UploadFile, File, Form, Request

from app.api.deps import require_permission, get_current_user
from app.schemas.object_id import PyObjectId
from app.schemas.requests import RegisterIn
from app.schemas.users import UserOut
from app.services.users import (
    get_user_service,
    get_users_service,
    delete_user_service,
    update_user_service,
    create_admin_service,
    read_profile_service,
    update_profile_service,
)

router = APIRouter()


@router.get(
    "/profile",
    response_model=UserOut,
    dependencies=[Depends(require_permission("users","Read"))],
)
async def get_profile(
    request: Request,
    current_user: Dict = Depends(get_current_user),
):
    """
    Get the currently logged-in user's profile.

    Returns:
        UserOut: Profile details of the authenticated user.
    """
    return await read_profile_service(current_user)


@router.put(
    "/profile-update",
    response_model=UserOut,
    dependencies=[Depends(require_permission("users","Read"))],
)
async def update_user(
    current_user: Dict = Depends(get_current_user),
    user_status_id: Optional[PyObjectId] = Form(None),
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    country_code: Optional[str] = Form(None),
    phone_no: Optional[str] = Form(None),
    image: UploadFile = File(None),
):
    """
    Update the logged-in user's profile.
    Supports optional profile image upload.

    Args:
        current_user: The authenticated user context.
        user_status_id: Optional new user_status_id.
        first_name, last_name, email, phone_no, country_code: Updatable fields.
        image: Optional new profile image.

    Returns:
        UserOut: Updated user details.
    """
    return await update_profile_service(
        current_user,
        user_status_id,
        first_name,
        last_name,
        email,
        country_code,
        phone_no,
        image,
    )


@router.post(
    "/create-admin",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("users", "Create"))],
)
async def create_user(payload: RegisterIn):
    """
    Create a new user with admin privileges.

    Args:
        payload (RegisterIn): Registration data.

    Returns:
        UserOut: Newly created admin user.
    """
    return await create_admin_service(payload)


@router.get(
    "/",
    response_model=List[UserOut],
    dependencies=[Depends(require_permission("users", "Read","admin"))],
)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    role_id: Optional[PyObjectId] = Query(None),
    user_status_id: Optional[PyObjectId] = Query(None),
):
    """
    List users with optional filtering.

    Args:
        skip: Pagination offset.
        limit: Max results.
        role_id: Filter by role.
        user_status_id: Filter by status.

    Returns:
        List[UserOut]: User list.
    """
    return await get_users_service(skip, limit, role_id, user_status_id)


@router.get(
    "/{user_id}",
    response_model=UserOut,
    dependencies=[Depends(require_permission("users", "Read","admin"))],
)
async def get_user(user_id: PyObjectId):
    """
    Get details for a specific user.

    Raises:
        HTTPException 404: If user does not exist.
    """
    return await get_user_service(user_id)


@router.put(
    "/{user_id}",
    response_model=UserOut,
    dependencies=[Depends(require_permission("users", "Update","admin"))],
)
async def update_user(user_id: PyObjectId, user_status_id: PyObjectId = Form(...)):
    """
    Update a user's status (admin only).

    Args:
        user_id: Target user.
        user_status_id: New status.

    Returns:
        UserOut: Updated user details.
    """
    return await update_user_service(user_id, user_status_id)


@router.delete(
    "/{user_id}",
    dependencies=[Depends(require_permission("users", "Delete"))],
)
async def delete_user(user_id: PyObjectId):
    """
    Delete a user (admin only).

    Raises:
        HTTPException 404: If user not found.
    """
    return await delete_user_service(user_id)