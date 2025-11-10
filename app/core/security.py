from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings
import uuid
from typing import Any, Dict, Optional
from fastapi.security import OAuth2PasswordBearer

# OAuth2 password scheme for FastAPI authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Password hashing context (supports bcrypt & bcrypt_sha256)
pwd_context = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto")


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plaintext password against a hashed password using passlib.

    Args:
        plain (str): Raw password entered by the user.
        hashed (str): Stored hashed password.

    Returns:
        bool: True if the password matches, otherwise False.
    """
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    Args:
        password (str): Raw password string.

    Returns:
        str: Hashed password suitable for storing in DB.
    """
    return pwd_context.hash(password)


def _utcnow() -> datetime:
    """
    Internal utility: Provides current timestamp in UTC timezone.

    Returns:
        datetime: UTC-aware timestamp.
    """
    return datetime.now(timezone.utc)


def _base_claims(payload: Dict[str, Any], token_type: str, expires_delta: timedelta) -> Dict[str, Any]:
    """
    Construct core JWT claims common to access & refresh tokens.

    Args:
        payload (Dict[str, Any]): Custom claims such as user_id.
        token_type (str): "access" or "refresh".
        expires_delta (timedelta): Expiry duration.

    Returns:
        Dict[str, Any]: Full JWT payload with exp, iat, jti, etc.
    """
    now = _utcnow()
    jti = str(uuid.uuid4())
    exp = now + expires_delta
    return {
        **payload,
        "type": token_type,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }


def create_access_token(payload: Dict[str, Any], expires_minutes: Optional[int] = None) -> Dict[str, Any]:
    """
    Create a signed JWT access token.

    Args:
        payload (Dict[str, Any]): Required claims (e.g., user_id).
        expires_minutes (Optional[int]): Custom expiration; defaults to settings.

    Returns:
        Dict[str, Any]: { "token": <jwt string>, "jti": <uuid>, "exp": <timestamp> }
    """
    minutes = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    claims = _base_claims(payload, "access", timedelta(minutes=minutes))
    token = jwt.encode(
        claims,
        settings.JWT_ACCESS_TOKEN_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    return {"token": token, "jti": claims["jti"], "exp": claims["exp"]}


def create_refresh_token(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a signed JWT refresh token.

    Args:
        payload (Dict[str, Any]): Required claims (e.g., user_id).

    Returns:
        Dict[str, Any]: { "token": <jwt string>, "jti": <uuid>, "exp": <timestamp> }
    """
    claims = _base_claims(
        payload,
        "refresh",
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    token = jwt.encode(
        claims,
        settings.JWT_REFRESH_TOKEN_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    return {"token": token, "jti": claims["jti"], "exp": claims["exp"]}


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode & validate an access token.

    Returns None if token is invalid, expired or tampered.

    Args:
        token (str): JWT string.

    Returns:
        Optional[Dict[str, Any]]: Claims dict or None.
    """
    try:
        return jwt.decode(
            token,
            settings.JWT_ACCESS_TOKEN_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        return None


def decode_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode & validate a refresh token.

    Returns None if token is invalid, expired or tampered.

    Args:
        token (str): JWT string.

    Returns:
        Optional[Dict[str, Any]]: Claims dict or None.
    """
    try:
        return jwt.decode(
            token,
            settings.JWT_REFRESH_TOKEN_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        return None