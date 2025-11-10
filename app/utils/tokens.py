import hashlib
from app.core.config import settings

def hash_refresh(raw_token: str) -> str:
    """
    Hash a refresh token before storing it in the database.

    This prevents storing refresh tokens in plain text and adds a security
    layer using a server-side secret (pepper).

    Args:
        raw_token (str): The raw refresh token string.

    Returns:
        str: A SHA-256 hashed hexadecimal string of (token + pepper).
    """
    data = (raw_token + settings.TOKEN_HASH_PEPPER).encode("utf-8")
    return hashlib.sha256(data).hexdigest()