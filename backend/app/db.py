from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings
from .models import Base

settings = get_settings()

_is_sqlite = settings.database_url.startswith("sqlite")
if _is_sqlite:
    db_path = settings.database_url.split("///", 1)[-1]
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    # pool_pre_ping transparently replaces connections dropped by Postgres
    # (restarts, idle timeouts) instead of failing the request.
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _apply_light_migrations()


def _apply_light_migrations() -> None:
    """Add columns introduced after a database was first created.

    The project has no migration tool yet; this keeps an existing volume usable
    instead of forcing a reset. Safe to run on every startup (idempotent).
    """
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "groups" in tables:
        columns = {col["name"] for col in inspector.get_columns("groups")}
        with engine.begin() as conn:
            if "reply_scope" not in columns:
                conn.execute(
                    text("ALTER TABLE groups ADD COLUMN reply_scope VARCHAR(16) DEFAULT 'relevant'")
                )
            if "max_replies_per_user_per_day" not in columns:
                conn.execute(
                    text(
                        "ALTER TABLE groups ADD COLUMN max_replies_per_user_per_day "
                        "INTEGER DEFAULT 2"
                    )
                )
    if "messages" in tables:
        columns = {col["name"] for col in inspector.get_columns("messages")}
        if "sender_id" not in columns:
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE messages ADD COLUMN sender_id BIGINT DEFAULT 0")
                )


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
