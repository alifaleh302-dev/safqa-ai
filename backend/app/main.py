import asyncio

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import current_user
from .config import get_settings
from .db import init_db
from .routers import accounts, auth, groups, knowledge, monitor, prompts
from .routers import settings as settings_router

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public: login + health.
app.include_router(auth.router)

# Protected: everything that touches accounts, prompts, groups, monitoring,
# settings or the knowledge base requires a valid Bearer token.
protected = [Depends(current_user)]
app.include_router(accounts.router, dependencies=protected)
app.include_router(prompts.router, dependencies=protected)
app.include_router(groups.router, dependencies=protected)
app.include_router(monitor.router)
app.include_router(settings_router.router, dependencies=protected)
app.include_router(knowledge.router, dependencies=protected)


@app.on_event("startup")
async def on_startup() -> None:
    # Postgres may still be starting when the backend boots; retry briefly.
    last_error: Exception | None = None
    for _ in range(15):
        try:
            init_db()
            break
        except Exception as exc:  # noqa: BLE001 - surfaced after retries
            last_error = exc
            await asyncio.sleep(2)
    else:
        raise RuntimeError(f"Database not reachable after retries: {last_error}")

    # Bring back accounts that were online before the last restart.
    asyncio.create_task(_restore_accounts())


async def _restore_accounts() -> None:
    from . import models
    from .db import SessionLocal
    from .services import telegram_manager

    if not settings.telegram_api_id or not settings.telegram_api_hash:
        return
    with SessionLocal() as db:
        ids = [
            a.id
            for a in db.query(models.Account).filter(models.Account.active.is_(True)).all()
            if a.session_enc
        ]

    for account_id in ids:
        try:
            await telegram_manager.connect_existing(account_id)
        except Exception:
            # A single bad session must not block the rest.
            continue


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name}
