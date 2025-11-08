# app/utils/crypto.py
from __future__ import annotations
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings

_f = None

def _fernet() -> Fernet:
    global _f
    if _f is None:
        key = settings.CARD_ENC_KEY.encode()
        _f = Fernet(key)
    return _f

def encrypt_card_no(card_no: str) -> str:
    """
    Encrypt card number and return url-safe base64 token (string).
    """
    f = _fernet()
    return f.encrypt(card_no.encode()).decode()

def decrypt_card_no(token: str) -> Optional[str]:
    """
    Decrypt token produced by encrypt_card_no. Raises InvalidToken if bad.
    """
    if not token:
        return None
    f = _fernet()
    try:
        plain = f.decrypt(token.encode())
    except InvalidToken:
        return None
    return plain.decode()