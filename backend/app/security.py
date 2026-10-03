import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from .config import get_settings


@lru_cache
def _fernet() -> Fernet:
    """Derive a stable Fernet key from SECRET_KEY.

    Falls back to a derived key when SECRET_KEY is unset so the MVP runs out of
    the box; set SECRET_KEY in production or sessions become unreadable after a
    restart if the fallback ever changes.
    """
    raw = get_settings().secret_key or "dev-insecure-secret-change-me"
    digest = hashlib.sha256(raw.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:  # pragma: no cover - defensive
        raise ValueError("Unable to decrypt stored session (wrong SECRET_KEY?)") from exc
