from pathlib import Path

from sqlalchemy import create_engine
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


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
