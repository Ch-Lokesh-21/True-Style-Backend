"""
Authentication Routes

Provides endpoints for:
- User registration
- Login and token issuance
- Access token refresh using refresh tokens
- Logout with token revocation
- Password change for logged-in users
- Forgot password request and verification flows
"""

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


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterIn):
    """
    Register a new user account.

    Args:
        payload (RegisterIn): User registration input data.

    Returns:
        UserOut: Created user object.
    """
    return await register_service(payload)


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    response: Response,
    request: Request,
    body: LoginIn | None = None,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Authenticate user credentials and issue access + refresh tokens.

    Supports:
      - Standard JSON login request body
      - `application/x-www-form-urlencoded` for Swagger UI

    Args:
        response (Response): Used to set refresh cookie.
        request (Request): Incoming HTTP request.
        body (LoginIn | None): Login body from frontend.
        form_data (OAuth2PasswordRequestForm): Login from Swagger (username/password).

    Returns:
        LoginResponse: Access token, user info and refresh cookie.
    """
    if body is None:
        body = LoginIn(email=form_data.username, password=form_data.password)
    return await login_service(response, request, body)


@router.post("/token/refresh", response_model=TokenRotatedOut, status_code=status.HTTP_200_OK)
async def token_refresh(
    response: Response,
    request: Request,
    rt: Optional[str] = Cookie(default=None, alias=settings.REFRESH_COOKIE_NAME),
):
    """
    Rotate access token using a valid refresh token stored in cookies.

    Args:
        response (Response): Used to update the refresh cookie.
        request (Request): HTTP request.
        rt (str | None): Refresh token from cookie.

    Returns:
        TokenRotatedOut: New access and refresh token (rotated).
    """
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
    token: str = Depends(oauth2_scheme),
    rt: Optional[str] = Cookie(default=None, alias=settings.REFRESH_COOKIE_NAME)
):
    """
    Logout user by revoking access + refresh tokens and clearing cookie.

    Args:
        response (Response): Clears cookie.
        request (Request)
        token (str): Access token sent in Authorization header.
        rt (str | None): Refresh token from cookie.

    Returns:
        MessageOut: Confirmation message.
    """
    return await logout_service(response, request, rt, token)


@router.post(
    "/change-password",
    response_model=MessageOut,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(oauth2_scheme)],
)
async def change_password(
    body: ChangePasswordIn,
    current=Depends(get_current_user),
):
    """
    Change the password of the currently authenticated user.

    Args:
        body (ChangePasswordIn): Contains old and new password.
        current: Current authenticated user.

    Returns:
        MessageOut: Confirmation message.
    """
    return await change_password_service(current, body)


@router.post("/forgot-password/request", response_model=MessageOut, status_code=status.HTTP_200_OK)
async def forgot_password_request(body: ForgotPasswordRequestIn):
    """
    Initiate forgot-password flow by sending OTP/email link.

    Args:
        body (ForgotPasswordRequestIn): Email or username.

    Returns:
        MessageOut: Status message.
    """
    return await forgot_password_request_service(body)


@router.post("/forgot-password/verify", response_model=MessageOut, status_code=status.HTTP_200_OK)
async def forgot_password_verify(body: ForgotPasswordVerifyIn):
    """
    Verify OTP/token and allow password reset.

    Args:
        body (ForgotPasswordVerifyIn): Email, OTP, and new password.

    Returns:
        MessageOut: Confirmation message.
    """
    return await forgot_password_verify_service(body)