from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db
from ..services import telegram_manager as tg

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.get("", response_model=list[schemas.GroupOut])
def list_groups(db: Session = Depends(get_db)):
    return db.query(models.Group).order_by(models.Group.id).all()


@router.post("", response_model=schemas.GroupOut, status_code=201)
def create_group(payload: schemas.GroupCreate, db: Session = Depends(get_db)):
    if db.query(models.Group).filter(models.Group.telegram_id == payload.telegram_id).first():
        raise HTTPException(409, "Group with this Telegram id already exists")
    group = models.Group(**payload.model_dump())
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.put("/{group_id}", response_model=schemas.GroupOut)
def update_group(group_id: int, payload: schemas.GroupUpdate, db: Session = Depends(get_db)):
    group = db.get(models.Group, group_id)
    if group is None:
        raise HTTPException(404, "Group not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(group, key, value)
    db.commit()
    db.refresh(group)
    return group


@router.delete("/{group_id}", status_code=204)
def delete_group(group_id: int, db: Session = Depends(get_db)):
    group = db.get(models.Group, group_id)
    if group is None:
        raise HTTPException(404, "Group not found")
    db.delete(group)
    db.commit()


@router.post("/{group_id}/resolve", response_model=schemas.GroupOut)
async def resolve_group(group_id: int, db: Session = Depends(get_db)):
    """Fetch the real group title using the bound account's live session."""
    group = db.get(models.Group, group_id)
    if group is None:
        raise HTTPException(404, "Group not found")
    if group.account_id is None:
        raise HTTPException(400, "Bind an account to this group first")
    title = await tg.resolve_group(group.account_id, group.telegram_id)
    if title:
        group.title = title
        db.commit()
        db.refresh(group)
    return group
