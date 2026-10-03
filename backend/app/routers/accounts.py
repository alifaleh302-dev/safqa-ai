from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import get_settings
from ..db import get_db
from ..services import telegram_manager as tg

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


def _to_out(account: models.Account) -> schemas.AccountOut:
    out = schemas.AccountOut.model_validate(account)
    out.has_session = bool(account.session_enc)
    return out


@router.get("", response_model=list[schemas.AccountOut])
def list_accounts(db: Session = Depends(get_db)):
    return [_to_out(a) for a in db.query(models.Account).order_by(models.Account.id).all()]


@router.post("", response_model=schemas.AccountOut, status_code=201)
def create_account(payload: schemas.AccountCreate, db: Session = Depends(get_db)):
    account = models.Account(label=payload.label, phone=payload.phone)
    db.add(account)
    db.commit()
    db.refresh(account)
    return _to_out(account)


@router.delete("/{account_id}", status_code=204)
async def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = db.get(models.Account, account_id)
    if account is None:
        raise HTTPException(404, "Account not found")
    await tg.disconnect(account_id)
    db.delete(account)
    db.commit()


@router.post("/{account_id}/send-code", response_model=schemas.AccountOut)
async def send_code(account_id: int, db: Session = Depends(get_db)):
    if not get_settings().telegram_api_id or not get_settings().telegram_api_hash:
        raise HTTPException(400, "Telegram API id/hash not configured in Settings")
    try:
        await tg.send_code(account_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    except Exception as exc:
        raise HTTPException(400, f"Telegram error: {exc}")
    db.expire_all()
    return _to_out(db.get(models.Account, account_id))


@router.post("/{account_id}/verify-code", response_model=schemas.AccountOut)
async def verify_code(account_id: int, payload: schemas.CodeRequest, db: Session = Depends(get_db)):
    try:
        result = await tg.submit_code(account_id, payload.code)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise HTTPException(400, f"Telegram error: {exc}")
    db.expire_all()
    out = _to_out(db.get(models.Account, account_id))
    if result == "password_required":
        out.status = "awaiting_password"
    return out


@router.post("/{account_id}/verify-password", response_model=schemas.AccountOut)
async def verify_password(account_id: int, payload: schemas.PasswordRequest, db: Session = Depends(get_db)):
    try:
        await tg.submit_password(account_id, payload.password)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise HTTPException(400, f"Telegram error: {exc}")
    db.expire_all()
    return _to_out(db.get(models.Account, account_id))


@router.post("/{account_id}/connect", response_model=schemas.AccountOut)
async def connect(account_id: int, db: Session = Depends(get_db)):
    try:
        await tg.connect_existing(account_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise HTTPException(400, f"Telegram error: {exc}")
    db.expire_all()
    return _to_out(db.get(models.Account, account_id))


@router.post("/{account_id}/disconnect", response_model=schemas.AccountOut)
async def disconnect(account_id: int, db: Session = Depends(get_db)):
    await tg.disconnect(account_id)
    db.expire_all()
    return _to_out(db.get(models.Account, account_id))
