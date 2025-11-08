from __future__ import annotations
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, Query, status, UploadFile, File, Form, Request
from app.api.deps import require_permission, get_current_user
from app.schemas.object_id import PyObjectId
from app.schemas.requests import RegisterIn
from app.schemas.users import UserOut
from app.services.users import get_user_service, get_users_service, delete_user_service, update_user_service, create_admin_service, read_profile_service, update_profile_service
router = APIRouter()

@router.get(
    "/profile",
    response_model=UserOut,
    dependencies=[Depends(require_permission("users","Read"))]
)
async def get_profile(request:Request , current_user: Dict = Depends(get_current_user)):
    return await read_profile_service(current_user)
    
@router.put(
    "/profile-update",
    response_model=UserOut,
    dependencies=[Depends(require_permission("users","Read"))]
)
async def update_user(
    current_user :Dict = Depends(get_current_user),
    user_status_id: Optional[PyObjectId] = Form(None),
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    country_code: Optional[str] = Form(None),
    phone_no: Optional[str] = Form(None),
    image: UploadFile = File(None)
    ):
    return await update_profile_service(current_user,user_status_id,first_name,last_name,email,country_code,phone_no,image)

@router.post(
    "/create-admin",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("users", "Create"))]
)
async def create_user(payload: RegisterIn):
    return await create_admin_service(payload)



@router.get(
    "/",
    response_model=List[UserOut],
    dependencies=[Depends(require_permission("users", "Read","admin"))]
)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    role_id: Optional[PyObjectId] = Query(None),
    user_status_id: Optional[PyObjectId] = Query(None),
):
    return await get_users_service(skip,limit,role_id,user_status_id)


@router.get(
    "/{user_id}",
    response_model=UserOut,
    dependencies=[Depends(require_permission("users", "Read","admin"))]
)
async def get_user(user_id: PyObjectId):
    return await get_user_service(user_id)

@router.put(
    "/{user_id}",
    response_model=UserOut,
    dependencies=[Depends(require_permission("users", "Update","admin"))]
)
async def update_user(user_id: PyObjectId, user_status_id: PyObjectId = Form(...)):
    return await update_user_service(user_id,user_status_id)

@router.delete(
    "/{user_id}",
    dependencies=[Depends(require_permission("users", "Delete"))]
)
async def delete_user(user_id: PyObjectId):
    return await delete_user_service(user_id)
