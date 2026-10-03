import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_settings

ALGORITHM = "HS256"
_bearer = HTTPBearer(auto_error=False)


def _jwt_secret() -> str:
    settings = get_settings()
    # Fall back to SECRET_KEY so a single secret can drive both features in dev.
    return settings.jwt_secret or settings.secret_key or "dev-insecure-jwt-secret"


def _password_digest(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_credentials(username: str, password: str) -> bool:
    """Constant-time comparison against the configured admin credentials."""
    settings = get_settings()
    user_ok = hmac.compare_digest(username, settings.admin_username)
    pass_ok = hmac.compare_digest(_password_digest(password), _password_digest(settings.admin_password))
    return user_ok and pass_ok


def create_access_token(username: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=ALGORITHM)


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str:
    """FastAPI dependency: require a valid Bearer token."""
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, _jwt_secret(), algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    username = payload.get("sub")
    if not username:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token payload")
    return username


def token_from_query(token: str | None) -> str:
    """Validate a token passed as a query param (WebSocket auth)."""
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[ALGORITHM])
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    return payload.get("sub") or ""
