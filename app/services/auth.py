from __future__ import annotations
from typing import Optional
from datetime import datetime, timezone
import random

from bson import ObjectId
from fastapi import HTTPException, Depends, status, Request, Response, Cookie

from app.core.database import db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    hash_password,
    decode_access_token,
    decode_refresh_token,
)
from app.core.config import settings
from app.api.deps import get_current_user
from app.utils.tokens import hash_refresh
from app.crud.sessions import (
    create_session,
    get_by_refresh_hash,
    revoke_session_by_jti,
)
from app.crud.token_revocations import add_revocation, is_revoked
from app.crud import users as crud
from app.schemas.users import UserOut, UserCreate
from app.schemas.responses import MessageOut, TokenRotatedOut, LoginResponse
from app.schemas.requests import (
    LoginIn,
    ChangePasswordIn,
    ForgotPasswordRequestIn,
    ForgotPasswordVerifyIn,
    RegisterIn,
)
from app.utils.fastapi_mail import _send_mail, generate_otp_email_html

# ------------------- helpers -------------------

def _unix_to_dt(ts: int) -> datetime:
    return datetime.fromtimestamp(ts, tz=timezone.utc)

def _set_refresh_cookie(response: Response, token: str, exp_ts: int) -> None:
    max_age = settings.REFRESH_COOKIE_MAX_AGE_DAYS * 86400
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
        path=settings.REFRESH_COOKIE_PATH,
        max_age=max_age,
        expires=exp_ts,
    )

def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path=settings.REFRESH_COOKIE_PATH,
    )

# ------------------- services -------------------

async def login_service(response: Response, request: Request, body: LoginIn) -> LoginResponse:
    try:
        email = body.email
        user = await db["users"].find_one({"email": email})
        if not user or not verify_password(body.password, user.get("password", "")):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
        user_status = await db["user_status"].find_one({"status":"blocked"})
        if str(user["user_status_id"])==str(user_status["_id"]):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "User account is suspended")

        # update last login (UTC)
        await db["users"].update_one(
            {"_id": user["_id"]},
            {"$set": {"last_login": datetime.now(timezone.utc)}},
        )
        wishlist = await db["wishlists"].find_one({"user_id":ObjectId(user["_id"])})
        
        cart = await db["carts"].find_one({"user_id":ObjectId(user["_id"])})
        payload = {
            "user_id": str(user["_id"]),
            "user_role_id": str(user["role_id"]),
            "wishlist_id": str(wishlist["_id"]),
            "cart_id": str(cart["_id"]),
            "type": "access_payload",
        }

        at = create_access_token(payload)
        rt = create_refresh_token(
            {
                "user_id": payload["user_id"],
                "user_role_id": payload["user_role_id"],
                "wishlist_id": payload["wishlist_id"],
                "cart_id": payload["cart_id"]
            }
        )

        sess = {
            "user_id": payload["user_id"],
            "jti": rt["jti"],
            "refresh_hash": hash_refresh(rt["token"]),
            "exp": _unix_to_dt(rt["exp"]),
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        }
        await create_session(sess)

        _set_refresh_cookie(response, rt["token"], rt["exp"])

        return LoginResponse(
            access_token=at["token"],
            access_jti=at["jti"],
            access_exp=at["exp"],
            payload={
                "user_id": payload["user_id"],
                "user_role_id": payload["user_role_id"],
                "wishlist_id": payload["wishlist_id"],
                "cart_id": payload["cart_id"]
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal Server Error") from e


async def register_service(payload: RegisterIn) -> UserOut:
    email = payload.email
    try:
        # uniqueness checks
        existing = await db["users"].find_one({"email": email})
        if existing:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")

        existing = await db["users"].find_one(
            {"phone_no": payload.phone_no, "country_code": payload.country_code}
        )
        if existing:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Phone number already registered")

        # default role & status
        role = await db["user_roles"].find_one({"role": "user"})
        if not role:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Default user role not found")
        role_id = str(role["_id"])

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
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Error during registration") from e


async def refresh_token_service(
    response: Response,
    request: Request,
    rt: Optional[str] = Cookie(default=None, alias=settings.REFRESH_COOKIE_NAME),
) -> TokenRotatedOut:
    try:
        if not rt:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No refresh cookie")

        payload = decode_refresh_token(rt)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

        if await is_revoked(payload.get("jti", "")):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token revoked")

        session = await get_by_refresh_hash(hash_refresh(rt))
        if not session:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session not found or revoked")

        # rotate the old refresh
        await revoke_session_by_jti(session["jti"], reason="refresh-used")
        await add_revocation(session["jti"], expiresAt=_unix_to_dt(payload["exp"]), reason="refresh-used")

        new_payload = {
            "user_id": payload["user_id"],
            "user_role_id": payload["user_role_id"],
            "wishlist_id": payload["wishlist_id"],
            "cart_id": payload["cart_id"]
        }
        at = create_access_token(new_payload)
        new_rt = create_refresh_token(new_payload)

        await create_session(
            {
                "user_id": new_payload["user_id"],
                "jti": new_rt["jti"],
                "refresh_hash": hash_refresh(new_rt["token"]),
                "exp": _unix_to_dt(new_rt["exp"]),
                "ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }
        )

        _set_refresh_cookie(response, new_rt["token"], new_rt["exp"])

        return TokenRotatedOut(access_token=at["token"], access_jti=at["jti"], access_exp=at["exp"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal Server Error") from e


async def logout_service(
    response: Response,
    request: Request,
    rt: Optional[str] = None,
    access_token: Optional[str] = None,
) -> MessageOut:
    try:
        # 🔹 Revoke access token 
        if access_token:
            ap = decode_access_token(access_token)
            if ap and ap.get("type") == "access":
                await add_revocation(
                    ap.get("jti", ""),
                    expiresAt=_unix_to_dt(ap["exp"]),
                    reason="logout-access",
                )

        # 🔹 Revoke refresh token (if cookie exists)
        if rt:
            payload = decode_refresh_token(rt)
            if payload and payload.get("type") == "refresh":
                session = await get_by_refresh_hash(hash_refresh(rt))
                if session:
                    await revoke_session_by_jti(session["jti"], reason="logout-refresh")
                    await add_revocation(
                        session["jti"],
                        expiresAt=_unix_to_dt(payload["exp"]),
                        reason="logout-refresh",
                    )

        # 🔹 Clear the refresh cookie
        _clear_refresh_cookie(response)

        return MessageOut(message="Logged out successfully")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal Server Error"
        ) from e


async def change_password_service(current=Depends(get_current_user), body: ChangePasswordIn = ...) -> MessageOut:
    try:
        user = await db["users"].find_one({"_id": ObjectId(current["user_id"])})
        if not user or not verify_password(body.old_password, user.get("password", "")):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")

        await db["users"].update_one(
            {"_id": user["_id"]},
            {"$set": {"password": hash_password(body.new_password)}},
        )
        return MessageOut(message="Password updated")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal Server Error") from e


async def forgot_password_request_service(body: ForgotPasswordRequestIn) -> MessageOut:
    try:
        email = body.email
        user = await db["users"].find_one({"email": email})
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

        otp = random.randint(100000, 999999)
        await db["users"].update_one({"_id": user["_id"]}, {"$set": {"otp": otp}})
        await _send_mail("Password Reset OTP", [email], generate_otp_email_html(otp))
        return MessageOut(message="OTP sent")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal Server Error") from e


async def forgot_password_verify_service(body: ForgotPasswordVerifyIn) -> MessageOut:
    try:
        email = body.email
        user = await db["users"].find_one({"email": email, "otp": body.otp})
        if not user:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid OTP")

        await db["users"].update_one(
            {"_id": user["_id"]},
            {"$set": {"password": hash_password(body.new_password), "otp": None}},
        )
        return MessageOut(message="Password reset successful")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal Server Error") from e