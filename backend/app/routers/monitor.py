from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db
from ..services import engine
from ..services.gemini import GeminiError

router = APIRouter(prefix="/api", tags=["monitor"])


@router.get("/events", response_model=list[schemas.EventOut])
def list_events(limit: int = 100, db: Session = Depends(get_db)):
    return (
        db.query(models.Event)
        .order_by(models.Event.id.desc())
        .limit(min(limit, 500))
        .all()
    )


@router.get("/messages", response_model=list[schemas.MessageOut])
def list_messages(group_id: int | None = None, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(models.Message)
    if group_id is not None:
        query = query.filter(models.Message.group_id == group_id)
    return query.order_by(models.Message.id.desc()).limit(min(limit, 500)).all()


@router.get("/decisions", response_model=list[schemas.DecisionOut])
def list_decisions(group_id: int | None = None, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(models.Decision)
    if group_id is not None:
        query = query.filter(models.Decision.group_id == group_id)
    return query.order_by(models.Decision.id.desc()).limit(min(limit, 500)).all()


@router.post("/test", response_model=schemas.TestMessageResponse)
async def test_message(payload: schemas.TestMessageRequest, db: Session = Depends(get_db)):
    """Playground: run the decision engine on a message WITHOUT sending to Telegram."""
    group = db.get(models.Group, payload.group_id)
    if group is None:
        raise HTTPException(404, "Group not found")
    prompt = db.get(models.Prompt, group.prompt_id) if group.prompt_id else None
    if prompt is None:
        raise HTTPException(400, "This group has no prompt bound")

    rows = (
        db.query(models.Message)
        .filter(models.Message.group_id == group.id)
        .order_by(models.Message.id.desc())
        .limit(15)
        .all()
    )
    history = engine.build_history(
        [{"direction": m.direction, "text": m.text, "sender_name": m.sender_name} for m in reversed(rows)],
        15,
    )
    try:
        decision = await engine.decide(prompt.system_text, history, payload.text, payload.sender_name)
    except GeminiError as exc:
        raise HTTPException(400, str(exc))
    return schemas.TestMessageResponse(action=decision.action, reply=decision.reply, reason=decision.reason)
