from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import current_user, token_from_query
from ..db import SessionLocal, get_db
from ..services import engine
from ..services.gemini import GeminiError
from ..services.ws_manager import manager

router = APIRouter(prefix="/api", tags=["monitor"])


@router.websocket("/ws")
async def live_events(websocket: WebSocket, token: str = Query(default="")) -> None:
    """Push new messages and decisions to the browser as they happen.

    Authenticated via ?token=<jwt> because browsers cannot set headers on a
    WebSocket handshake. An unauthenticated client is closed before joining.
    """
    try:
        token_from_query(token)
    except HTTPException:
        await websocket.close(code=4401)
        return

    await manager.connect(websocket)
    try:
        # Prime the client with recent state so the UI is never empty on connect.
        with SessionLocal() as db:
            recent_messages = [
                schemas.MessageOut.model_validate(m).model_dump(mode="json")
                for m in db.query(models.Message).order_by(models.Message.id.desc()).limit(50).all()
            ]
            recent_decisions = [
                schemas.DecisionOut.model_validate(d).model_dump(mode="json")
                for d in db.query(models.Decision).order_by(models.Decision.id.desc()).limit(50).all()
            ]
        await websocket.send_json({"type": "snapshot", "data": {"messages": recent_messages, "decisions": recent_decisions}})
        while True:
            # Keep the connection open; client pings are ignored but keep it alive.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await manager.disconnect(websocket)


@router.get("/events", response_model=list[schemas.EventOut])
def list_events(limit: int = 100, db: Session = Depends(get_db), _: str = Depends(current_user)):
    return (
        db.query(models.Event)
        .order_by(models.Event.id.desc())
        .limit(min(limit, 500))
        .all()
    )


@router.get("/messages", response_model=list[schemas.MessageOut])
def list_messages(group_id: int | None = None, limit: int = 100, db: Session = Depends(get_db), _: str = Depends(current_user)):
    query = db.query(models.Message)
    if group_id is not None:
        query = query.filter(models.Message.group_id == group_id)
    return query.order_by(models.Message.id.desc()).limit(min(limit, 500)).all()


@router.get("/decisions", response_model=list[schemas.DecisionOut])
def list_decisions(group_id: int | None = None, limit: int = 100, db: Session = Depends(get_db), _: str = Depends(current_user)):
    query = db.query(models.Decision)
    if group_id is not None:
        query = query.filter(models.Decision.group_id == group_id)
    return query.order_by(models.Decision.id.desc()).limit(min(limit, 500)).all()


@router.post("/test", response_model=schemas.TestMessageResponse)
async def test_message(payload: schemas.TestMessageRequest, db: Session = Depends(get_db), _: str = Depends(current_user)):
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
        decision = await engine.decide(
            prompt.system_text, history, payload.text, payload.sender_name, reply_scope=group.reply_scope
        )
    except GeminiError as exc:
        raise HTTPException(400, str(exc))
    return schemas.TestMessageResponse(action=decision.action, reply=decision.reply, reason=decision.reason)
