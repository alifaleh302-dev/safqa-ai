from functools import lru_cache
from pathlib import Path

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
    gemini_model: str = "gemini-1.5-flash"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"

    # Fernet key used to encrypt Telethon session strings at rest
    secret_key: str = ""

    # Human-like behavior defaults
    reply_min_delay: float = 2.0
    reply_max_delay: float = 9.0
    max_context_messages: int = 15

    # Per-account anti-spam guard
    max_replies_per_hour: int = 20
    max_replies_per_day: int = 200


@lru_cache
def get_settings() -> Settings:
    return Settings()
