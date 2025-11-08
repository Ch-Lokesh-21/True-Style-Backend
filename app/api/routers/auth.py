from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, Request, Response, Cookie, status
from fastapi.security import OAuth2PasswordRequestForm
from app.core.security import oauth2_scheme
from app.core.config import settings
from app.api.deps import get_current_user
from app.schemas.users import UserOut
from app.schemas.responses import MessageOut, TokenRotatedOut, LoginResponse
from app.schemas.requests import (
    LoginIn,
    ChangePasswordIn,
    ForgotPasswordRequestIn,
    ForgotPasswordVerifyIn,
    RegisterIn,
)
from app.services.auth import (
    register_service,
    login_service,
    refresh_token_service,
    logout_service,
    change_password_service,
    forgot_password_request_service,
    forgot_password_verify_service,
)

router = APIRouter()

# ------------------- routes -------------------

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterIn):
    return await register_service(payload)




@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    response: Response,
    request: Request,
    body: LoginIn | None = None,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    # Support both form (Swagger) and JSON (Any frontend)
    if body is None:
        body = LoginIn(email=form_data.username, password=form_data.password)
    return await login_service(response, request, body)



@router.post("/token/refresh", response_model=TokenRotatedOut, status_code=status.HTTP_200_OK)
async def token_refresh(
    response: Response,
    request: Request,
    rt: Optional[str] = Cookie(default=None, alias=settings.REFRESH_COOKIE_NAME),
):
    return await refresh_token_service(response, request, rt)


@router.post(
    "/logout",
    response_model=MessageOut,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(oauth2_scheme)],
)
async def logout(
    response: Response,
    request: Request,
    token:str = Depends(oauth2_scheme),
    rt: Optional[str] = Cookie(default=None, alias=settings.REFRESH_COOKIE_NAME)
):
    return await logout_service(response, request, rt,token)


@router.post("/change-password", response_model=MessageOut, status_code=status.HTTP_200_OK, dependencies=[Depends(oauth2_scheme)])
async def change_password(
    body: ChangePasswordIn,
    current=Depends(get_current_user),
):
    # keep service signature (current first), it uses the user id to verify & update
    return await change_password_service(current, body)


@router.post("/forgot-password/request", response_model=MessageOut, status_code=status.HTTP_200_OK)
async def forgot_password_request(body: ForgotPasswordRequestIn):
    return await forgot_password_request_service(body)


@router.post("/forgot-password/verify", response_model=MessageOut, status_code=status.HTTP_200_OK)
async def forgot_password_verify(body: ForgotPasswordVerifyIn):
    return await forgot_password_verify_service(body)