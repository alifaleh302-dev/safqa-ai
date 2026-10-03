from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Telegram AI Negotiator"
    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'app.db'}"

    # Telegram API credentials (my.telegram.org)
    telegram_api_id: int = 0
    telegram_api_hash: str = ""

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"
    # Comma-separated fallbacks tried when the primary model is unavailable.
    gemini_fallback_models: str = "gemini-flash-lite-latest,gemini-3.5-flash"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"

    # Fernet key used to encrypt Telethon session strings at rest
    secret_key: str = ""

    # Admin auth (JWT)
    admin_username: str = "admin"
    admin_password: str = "admin"
    jwt_secret: str = ""
    jwt_expire_minutes: int = 720

    # Human-like behavior defaults
    reply_min_delay: float = 2.0
    reply_max_delay: float = 9.0
    max_context_messages: int = 15

    # Per-account anti-spam guard
    max_replies_per_hour: int = 20
    max_replies_per_day: int = 200

    @field_validator("telegram_api_id", mode="before")
    @classmethod
    def _empty_int_to_zero(cls, value):
        # .env files routinely leave optional ints blank; treat "" as unset.
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return 0
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
