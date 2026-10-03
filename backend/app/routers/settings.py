import os
from pathlib import Path

from fastapi import APIRouter

from .. import schemas
from ..config import BASE_DIR, get_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])

ENV_PATH = BASE_DIR / ".env"


def _read_env() -> dict[str, str]:
    if not ENV_PATH.exists():
        return {}
    data: dict[str, str] = {}
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def _write_env(data: dict[str, str]) -> None:
    ENV_PATH.write_text("\n".join(f"{k}={v}" for k, v in data.items()) + "\n")


@router.get("", response_model=schemas.SettingsOut)
def read_settings():
    settings = get_settings()
    return schemas.SettingsOut(
        app_name=settings.app_name,
        telegram_api_id=settings.telegram_api_id,
        telegram_api_configured=bool(settings.telegram_api_id and settings.telegram_api_hash),
        gemini_configured=bool(settings.gemini_api_key),
        gemini_model=settings.gemini_model,
        max_context_messages=settings.max_context_messages,
        max_replies_per_hour=settings.max_replies_per_hour,
        max_replies_per_day=settings.max_replies_per_day,
    )


@router.put("", response_model=schemas.SettingsOut)
def update_settings(payload: schemas.SettingsUpdate):
    """Persist settings to .env. Only provided fields are written."""
    data = _read_env()
    mapping = {
        "TELEGRAM_API_ID": payload.telegram_api_id,
        "TELEGRAM_API_HASH": payload.telegram_api_hash,
        "GEMINI_API_KEY": payload.gemini_api_key,
        "GEMINI_MODEL": payload.gemini_model,
        "REPLY_MIN_DELAY": payload.reply_min_delay,
        "REPLY_MAX_DELAY": payload.reply_max_delay,
        "MAX_REPLIES_PER_HOUR": payload.max_replies_per_hour,
        "MAX_REPLIES_PER_DAY": payload.max_replies_per_day,
    }
    for key, value in mapping.items():
        if value is not None:
            data[key] = str(value)
    _write_env(data)

    # Refresh the process environment and the cached settings object.
    for key, value in data.items():
        os.environ[key] = value
    get_settings.cache_clear()
    return read_settings()
