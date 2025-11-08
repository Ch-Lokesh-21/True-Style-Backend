from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings
import uuid
from typing import Any, Dict, Optional
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
pwd_context = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto")

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

def _base_claims(payload: Dict[str, Any], token_type: str, expires_delta: timedelta) -> Dict[str, Any]:
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
    minutes = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    claims = _base_claims(payload, "access", timedelta(minutes=minutes))
    token = jwt.encode(claims, settings.JWT_ACCESS_TOKEN_SECRET, algorithm=settings.JWT_ALGORITHM)
    return {"token": token, "jti": claims["jti"], "exp": claims["exp"]}

def create_refresh_token(payload: Dict[str, Any]) -> Dict[str, Any]:
    claims = _base_claims(payload, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
    token = jwt.encode(claims, settings.JWT_REFRESH_TOKEN_SECRET, algorithm=settings.JWT_ALGORITHM)
    return {"token": token, "jti": claims["jti"], "exp": claims["exp"]}

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, settings.JWT_ACCESS_TOKEN_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None

def decode_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, settings.JWT_REFRESH_TOKEN_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None
