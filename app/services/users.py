from __future__ import annotations
from typing import List, Optional, Dict, Any
from fastapi import Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pymongo.errors import DuplicateKeyError
from app.api.deps import require_permission, get_current_user
from app.schemas.object_id import PyObjectId
from app.schemas.requests import RegisterIn
from app.schemas.users import UserCreate, UserUpdate, UserOut
from app.utils.gridfs import replace_image, delete_image, _extract_file_id_from_url
from app.core.database import db
from app.crud import users as crud


async def read_profile_service(current_user: Dict = Depends(get_current_user)) -> Optional[UserOut]:
    """
    Fetch the profile of the currently authenticated user.

    Args:
        current_user (Dict): Injected authenticated user payload.

    Returns:
        UserOut: User profile information.

    Raises:
        HTTPException: If user does not exist or internal errors occur.
    """
    try:
        d = await crud.get_one(PyObjectId(current_user["user_id"]))
        if not d:
            raise HTTPException(status_code=404, detail="User not found")
        return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user: {e}")


async def update_profile_service(
    current_user: Dict = Depends(get_current_user),
    user_status_id: Optional[PyObjectId] = Form(None),
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    country_code: Optional[str] = Form(None),
    phone_no: Optional[str] = Form(None),
    image: UploadFile = File(None),
) -> Optional[UserOut]:
    """
    Update logged-in user's profile and profile picture.

    Supports partial update. Replaces existing profile image if a new file is uploaded.

    Args:
        current_user (Dict): Authenticated user payload.
        user_status_id (PyObjectId | None): New status.
        first_name, last_name, email, country_code, phone_no: Updated fields.
        image (UploadFile | None): New profile image.

    Returns:
        UserOut: Updated user data.

    Raises:
        HTTPException: If no fields provided, invalid user, or DB conflicts.
    """
    try:
        current = await crud.get_one(PyObjectId(current_user["user_id"]))
        if not current:
            raise HTTPException(status_code=404, detail="User not found")

        patch = UserUpdate()

        if image is not None:
            old_id = _extract_file_id_from_url(current.profile_img_url)
            _, new_url = await replace_image(old_id, image)
            patch.profile_img_url = new_url

        if user_status_id is not None:
            patch.user_status_id = user_status_id
        if first_name is not None:
            patch.first_name = first_name
        if last_name is not None:
            patch.last_name = last_name
        if email is not None:
            patch.email = email
        if country_code is not None:
            patch.country_code = country_code
        if phone_no is not None:
            patch.phone_no = phone_no

        if not any(v is not None for v in patch.model_dump().values()):
            raise HTTPException(status_code=400, detail="No fields provided for update")

        updated = await crud.update_one(current_user["user_id"], patch)
        if not updated:
            raise HTTPException(status_code=404, detail="User not found")
        return updated

    except HTTPException:
        raise
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Field already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update user: {e}")


async def create_admin_service(payload: RegisterIn) -> Optional[UserOut]:
    """
    Create a new admin user.

    Automatically assigns admin role and active status.

    Args:
        payload (RegisterIn): Registration data.

    Returns:
        UserOut: Created admin user.

    Raises:
        HTTPException: On duplicate email or missing role/status defaults.
    """
    try:
        existing = await crud.get_by_email(payload.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")

        role = await db["user_roles"].find_one({"role": "admin"})
        if not role:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Default user role not found")
        role_id = role["_id"]

        status_doc = await db["user_status"].find_one({"status": "active"})
        if not status_doc:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Default user status not found")
        user_status_id = status_doc["_id"]

        doc = UserCreate(
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email,
            password=payload.password,
            country_code=payload.country_code,
            phone_no=payload.phone_no,
            role_id=role_id,
            user_status_id=user_status_id,
            last_login=None,
        )
        return await crud.create(doc)
    except HTTPException:
        raise
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Email already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create user: {e}")


async def get_users_service(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    role_id: Optional[PyObjectId] = Query(None),
    user_status_id: Optional[PyObjectId] = Query(None),
) -> List[UserOut]:
    """
    Get paginated list of all users with optional filters.

    Args:
        skip (int): Offset for pagination.
        limit (int): Page size.
        role_id (PyObjectId | None): Filter by role.
        user_status_id (PyObjectId | None): Filter by user status.

    Returns:
        List[UserOut]: List of matching users.

    Raises:
        HTTPException: If database fetch fails.
    """
    try:
        q: Dict[str, Any] = {}
        if role_id:
            q["role_id"] = role_id
        if user_status_id is not None:
            q["user_status_id"] = user_status_id
        return await crud.list_all(skip=skip, limit=limit, query=q or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list users: {e}")


async def get_user_service(user_id: PyObjectId) -> Optional[UserOut]:
    """
    Fetch a single user by ID.

    Args:
        user_id (PyObjectId): User ID to retrieve.

    Returns:
        UserOut: Matching user.

    Raises:
        HTTPException: If missing or internal error occurs.
    """
    try:
        d = await crud.get_one(user_id)
        if not d:
            raise HTTPException(status_code=404, detail="User not found")
        return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user: {e}")


async def update_user_service(user_id: PyObjectId, user_status_id: PyObjectId = Form(...)) -> Optional[UserOut]:
    """
    Update a user's status (admin privilege use-case).

    Args:
        user_id (PyObjectId): User to modify.
        user_status_id (PyObjectId): New status to apply.

    Returns:
        UserOut: Updated user data.

    Raises:
        HTTPException: On invalid data or conflicts.
    """
    try:
        current = await crud.get_one(user_id)
        if not current:
            raise HTTPException(status_code=404, detail="User not found")

        patch = UserUpdate()
        if user_status_id is not None:
            patch.user_status_id = user_status_id

        updated = await crud.update_one(user_id, patch)
        if not updated:
            raise HTTPException(status_code=404, detail="User not found")
        return updated

    except HTTPException:
        raise
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Field already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update user: {e}")


async def delete_user_service(user_id: PyObjectId) -> JSONResponse:
    """
    Delete a user and associated profile image from GridFS.

    Args:
        user_id (PyObjectId): User to delete.

    Returns:
        JSONResponse: {"deleted": True}

    Raises:
        HTTPException: If user not found or delete fails.
    """
    try:
        cur_user = await crud.get_one(user_id)
        if not cur_user:
            raise HTTPException(status_code=404, detail="User not found")

        ok = await crud.delete_one(user_id)
        if not ok:
            raise HTTPException(status_code=400, detail="Unable to delete user")

        file_id = _extract_file_id_from_url(cur_user.profile_img_url)
        if file_id:
            await delete_image(file_id)

        return JSONResponse(status_code=200, content={"deleted": True})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {e}")