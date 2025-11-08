import hashlib
from app.core.config import settings

def hash_refresh(raw_token: str) -> str:
    data = (raw_token + settings.TOKEN_HASH_PEPPER).encode("utf-8")
    return hashlib.sha256(data).hexdigest()
