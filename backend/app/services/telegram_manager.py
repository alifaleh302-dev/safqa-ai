import asyncio
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import User

from .. import models, schemas, security
from ..config import get_settings
from ..db import SessionLocal
from . import engine, humanize
from .gemini import GeminiError
from .ws_manager import publish as ws_publish

# One in-memory Telegram client per account id.
_clients: dict[int, TelegramClient] = {}
_handlers: dict[int, object] = {}

# Background supervisors that watch each client and reconnect it if it drops.
_supervisors: dict[int, asyncio.Task] = {}

# Simple in-memory anti-spam counters keyed by account id.
_reply_log: dict[int, list[datetime]] = defaultdict(list)

# Sign-in flows in progress, keyed by account id.
_pending: dict[int, dict] = {}

RECONNECT_MAX_BACKOFF = 300  # seconds
# Telegram clears the "typing…" status after a few seconds, so it is re-sent at
# this interval while the agent is "composing" a reply.
TYPING_PING_INTERVAL = 4.0


def is_connected(account_id: int) -> bool:
    client = _clients.get(account_id)
    return bool(client and client.is_connected())


def has_handler(account_id: int) -> bool:
    return account_id in _handlers


def pending_accounts() -> list[int]:
    return list(_pending.keys())


async def _build_client(account: models.Account) -> TelegramClient:
    settings = get_settings()
    session_str = security.decrypt(account.session_enc) if account.session_enc else ""
    client = TelegramClient(
        StringSession(session_str),
        settings.telegram_api_id,
        settings.telegram_api_hash,
        device_model="Desktop",
        system_version="Windows 10",
        app_version="4.16.8",
    )
    return client


def _persist_session(account_id: int, client: TelegramClient) -> None:
    """Save the Telethon StringSession back to the DB, encrypted."""
    session_str = StringSession.save(client.session)
    with SessionLocal() as db:
        account = db.get(models.Account, account_id)
        if account is None:
            return
        account.session_enc = security.encrypt(session_str)
        db.commit()


async def send_code(account_id: int) -> None:
    """Start a login flow: send the Telegram code to the account's phone."""
    with SessionLocal() as db:
        account = db.get(models.Account, account_id)
        if account is None:
            raise ValueError("Account not found")
        phone = account.phone
        client = await _build_client(account)

    await client.connect()
    sent = await client.send_code_request(phone)
    _pending[account_id] = {"client": client, "phone": phone, "phone_code_hash": sent.phone_code_hash}
    with SessionLocal() as db:
        account = db.get(models.Account, account_id)
        account.status = "awaiting_code"
        db.commit()


async def submit_code(account_id: int, code: str) -> str:
    state = _pending.get(account_id)
    if state is None:
        raise ValueError("No sign-in in progress for this account")
    client: TelegramClient = state["client"]
    try:
        await client.sign_in(phone=state["phone"], code=code, phone_code_hash=state["phone_code_hash"])
    except Exception as exc:  # telethon raises SessionPasswordNeededError for 2FA
        if exc.__class__.__name__ == "SessionPasswordNeededError":
            with SessionLocal() as db:
                account = db.get(models.Account, account_id)
                account.status = "awaiting_password"
                db.commit()
            return "password_required"
        raise

    _persist_session(account_id, client)
    _pending.pop(account_id, None)
    await _register(account_id, client)
    return "connected"


async def submit_password(account_id: int, password: str) -> str:
    state = _pending.get(account_id)
    if state is None:
        raise ValueError("No sign-in in progress for this account")
    client: TelegramClient = state["client"]
    await client.sign_in(password=password)
    _persist_session(account_id, client)
    _pending.pop(account_id, None)
    await _register(account_id, client)
    return "connected"


async def connect_existing(account_id: int) -> str:
    """Reconnect a previously authenticated account using its stored session."""
    with SessionLocal() as db:
        account = db.get(models.Account, account_id)
        if account is None:
            raise ValueError("Account not found")
        if not account.session_enc:
            raise ValueError("Account has no saved session; sign in first")
        client = await _build_client(account)

    await client.connect()
    if not await client.is_user_authorized():
        raise ValueError("Stored session is no longer authorized; sign in again")
    await _register(account_id, client)
    return "connected"


async def _register(account_id: int, client: TelegramClient) -> None:
    """Attach the new-message handler and update account status."""
    if account_id in _handlers:
        try:
            client.remove_event_handler(_handlers[account_id])
        except Exception:
            pass

    async def on_new_message(event: events.NewMessage.Event) -> None:
        await _handle_incoming(account_id, event)

    client.add_event_handler(on_new_message, events.NewMessage(incoming=True))
    _handlers[account_id] = on_new_message
    _clients[account_id] = client

    me = await client.get_me()
    with SessionLocal() as db:
        account = db.get(models.Account, account_id)
        account.status = "online"
        account.label = account.label or (me.username or me.first_name or account.phone)
        db.commit()

    _start_supervisor(account_id)


def _start_supervisor(account_id: int) -> None:
    """Ensure a single reconnect watcher is running for this account."""
    existing = _supervisors.get(account_id)
    if existing is not None and not existing.done():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    _supervisors[account_id] = loop.create_task(_supervise(account_id))


def _stop_supervisor(account_id: int) -> None:
    task = _supervisors.pop(account_id, None)
    if task is not None and not task.done():
        task.cancel()


async def _supervise(account_id: int) -> None:
    """Watch a client's connection and reconnect with exponential backoff.

    Telethon's own auto-reconnect handles short blips; this loop covers the
    cases it does not — the session being revoked, the client having been
    disconnected, or repeated failures — and keeps the account status in the
    DB (and the live UI) truthful.
    """
    attempt = 0
    while True:
        await asyncio.sleep(5)
        client = _clients.get(account_id)
        if client is None:
            return
        try:
            if client.is_connected():
                attempt = 0
                continue
            _log_event("warning", "telegram", f"account {account_id} disconnected; reconnecting")
            attempt += 1
            await client.connect()
            if not await client.is_user_authorized():
                raise RuntimeError("session no longer authorized")
            # Re-attach handlers in case the client object was replaced.
            async def on_new_message(event: events.NewMessage.Event) -> None:
                await _handle_incoming(account_id, event)

            client.remove_event_handler(_handlers.get(account_id, on_new_message))
            client.add_event_handler(on_new_message, events.NewMessage(incoming=True))
            _handlers[account_id] = on_new_message
            _clients[account_id] = client
            _set_status(account_id, "online")
            _log_event("info", "telegram", f"account {account_id} reconnected")
            attempt = 0
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - keep the loop alive
            _set_status(account_id, "offline")
            _log_event("error", "telegram", f"account {account_id} reconnect failed: {exc}")
            backoff = min(RECONNECT_MAX_BACKOFF, 5 * 2 ** min(attempt, 6))
            await asyncio.sleep(backoff)


def _set_status(account_id: int, status: str) -> None:
    with SessionLocal() as db:
        account = db.get(models.Account, account_id)
        if account is not None:
            account.status = status
            db.commit()


async def disconnect(account_id: int) -> None:
    _stop_supervisor(account_id)
    client = _clients.pop(account_id, None)
    if client is not None:
        try:
            await client.disconnect()
        except Exception:
            pass
    _set_status(account_id, "offline")


# ---------------------------------------------------------------------------
# Incoming message pipeline
# ---------------------------------------------------------------------------

def _check_rate_limit(account_id: int) -> bool:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    log = _reply_log[account_id]
    _reply_log[account_id] = [t for t in log if now - t < timedelta(days=1)]
    log = _reply_log[account_id]
    hour_count = sum(1 for t in log if now - t < timedelta(hours=1))
    if hour_count >= settings.max_replies_per_hour:
        return False
    if len(log) >= settings.max_replies_per_day:
        return False
    return True


def _record_reply(account_id: int) -> None:
    _reply_log[account_id].append(datetime.now(timezone.utc))


async def _handle_incoming(account_id: int, event: events.NewMessage.Event) -> None:
    """Full pipeline: filter -> context -> decide -> humanize -> send -> log."""
    try:
        chat = await event.get_chat()
        chat_id = event.chat_id
        text = event.raw_text or ""
        if not text.strip():
            return

        with SessionLocal() as db:
            group = db.query(models.Group).filter(models.Group.telegram_id == chat_id).first()
            if group is None or not group.active or group.account_id != account_id:
                return
            group_id = group.id
            prompt = db.get(models.Prompt, group.prompt_id) if group.prompt_id else None
            if prompt is None or not prompt.active:
                return
            system_text = prompt.system_text
            mode = group.mode
            reply_scope = group.reply_scope

            sender = await event.get_sender()
            sender_name = _display_name(sender)

            # Store inbound message (also broadcast to live monitor).
            inbound = models.Message(
                group_id=group_id,
                telegram_message_id=event.id,
                sender_name=sender_name,
                direction="in",
                text=text,
            )
            db.add(inbound)
            db.commit()
            db.refresh(inbound)
            inbound_id = inbound.id
            inbound_payload = {
                "id": inbound.id,
                "group_id": inbound.group_id,
                "sender_name": inbound.sender_name,
                "direction": inbound.direction,
                "text": inbound.text,
                "created_at": inbound.created_at.isoformat(),
            }

            history_rows = (
                db.query(models.Message)
                .filter(models.Message.group_id == group_id)
                .order_by(models.Message.id.desc())
                .limit(get_settings().max_context_messages)
                .all()
            )
            history = [
                {"direction": m.direction, "text": m.text, "sender_name": m.sender_name}
                for m in reversed(history_rows)
            ]

        ws_publish("message", inbound_payload)

        if mode == "off" or not _should_respond(mode, event, group_id):
            _log_decision(group_id, inbound_id, "ignore", "", "mode/filter: not addressed to us")
            return

        if not _check_rate_limit(account_id):
            _log_decision(group_id, inbound_id, "ignore", "", "rate limit reached")
            _log_event("warning", "guard", "Reply skipped: hourly/daily rate limit reached")
            return

        try:
            decision = await engine.decide(
                system_text,
                engine.build_history(history[:-1], get_settings().max_context_messages),
                text,
                sender_name,
                reply_scope=reply_scope,
            )
        except GeminiError as exc:
            _log_decision(group_id, inbound_id, "escalate", "", f"AI error: {exc}")
            _log_event("error", "ai", str(exc))
            return

        _log_decision(group_id, inbound_id, decision.action, decision.reply, decision.reason)

        if decision.action != "reply" or not decision.reply:
            return

        await humanize.human_pause(humanize.reading_delay(text))
        await _send_human(account_id, chat_id, decision.reply, group_id)
        _record_reply(account_id)
    except Exception as exc:  # pragma: no cover - keep the listener alive
        _log_event("error", "listener", f"Unhandled error in pipeline: {exc}")


def _display_name(sender) -> str:
    if isinstance(sender, User):
        return sender.first_name or sender.username or "Client"
    return getattr(sender, "title", "Client")


def _should_respond(mode: str, event: events.NewMessage.Event, group_id: int) -> bool:
    if mode == "always":
        return True
    # mention mode: only when the account is mentioned or the client replies to us.
    if getattr(event.message, "mentioned", False):
        return True
    reply_to = getattr(event.message, "reply_to_msg_id", None)
    if reply_to:
        with SessionLocal() as db:
            ours = (
                db.query(models.Message)
                .filter(
                    models.Message.group_id == group_id,
                    models.Message.telegram_message_id == reply_to,
                    models.Message.direction == "out",
                )
                .first()
            )
            if ours is not None:
                return True
    return False


async def _show_typing(client, chat_id: int, duration: float) -> None:
    """Keep the 'typing…' status visible for roughly `duration` seconds.

    Telegram clears the status after a few seconds, so it must be re-sent until
    the planned typing time elapses. Failures are swallowed: the indicator is
    cosmetic and must never block or fail the actual reply.
    """
    try:
        async with client.action(chat_id, "typing"):
            remaining = duration
            while remaining > 0:
                await humanize.human_pause(min(TYPING_PING_INTERVAL, remaining))
                remaining -= TYPING_PING_INTERVAL
    except Exception:  # noqa: BLE001 - best-effort cosmetic status
        pass


async def _send_human(account_id: int, chat_id: int, reply: str, group_id: int) -> None:
    client = _clients.get(account_id)
    if client is None:
        _log_event("warning", "telegram", f"account {account_id} not connected; reply skipped")
        return
    bubbles = humanize.split_message(reply)
    for i, bubble in enumerate(bubbles):
        if not bubble:
            continue
        await _show_typing(client, chat_id, humanize.typing_delay(bubble))
        try:
            sent = await client.send_message(chat_id, bubble)
        except Exception as exc:  # noqa: BLE001 - network blips are expected
            # One reconnect attempt, then let the supervisor take over.
            _log_event("warning", "telegram", f"send failed, retrying after reconnect: {exc}")
            try:
                await client.connect()
                sent = await client.send_message(chat_id, bubble)
            except Exception as exc2:  # noqa: BLE001
                _log_event("error", "telegram", f"send failed permanently: {exc2}")
                return
        _store_message(
            group_id=group_id,
            telegram_message_id=getattr(sent, "id", 0),
            sender_name="me",
            direction="out",
            text=bubble,
        )
        if i < len(bubbles) - 1:
            await humanize.human_pause(random_bubble_gap())


def random_bubble_gap() -> float:
    import random

    return random.uniform(0.8, 2.5)


# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

def _log_decision(group_id: int, message_id: Optional[int], action: str, reply: str, reason: str) -> None:
    with SessionLocal() as db:
        decision = models.Decision(
            group_id=group_id,
            message_id=message_id,
            action=action,
            reply_text=reply,
            reason=reason,
        )
        db.add(decision)
        db.commit()
        db.refresh(decision)
        payload = {
            "id": decision.id,
            "group_id": decision.group_id,
            "action": decision.action,
            "reply_text": decision.reply_text,
            "reason": decision.reason,
            "created_at": decision.created_at.isoformat(),
        }
    ws_publish("decision", payload)


def _log_event(level: str, source: str, message: str) -> None:
    with SessionLocal() as db:
        event = models.Event(level=level, source=source, message=message)
        db.add(event)
        db.commit()
        db.refresh(event)
        payload = {
            "id": event.id,
            "level": event.level,
            "source": event.source,
            "message": event.message,
            "created_at": event.created_at.isoformat(),
        }
    ws_publish("event", payload)


def log_warning(message: str) -> None:
    _log_event("warning", "config", message)


def _store_message(
    group_id: int,
    telegram_message_id: int,
    sender_name: str,
    direction: str,
    text: str,
) -> None:
    with SessionLocal() as db:
        message = models.Message(
            group_id=group_id,
            telegram_message_id=telegram_message_id,
            sender_name=sender_name,
            direction=direction,
            text=text,
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        payload = {
            "id": message.id,
            "group_id": message.group_id,
            "sender_name": message.sender_name,
            "direction": message.direction,
            "text": message.text,
            "created_at": message.created_at.isoformat(),
        }
    ws_publish("message", payload)


async def resolve_group(account_id: int, telegram_id: int) -> str:
    """Resolve a group title using a connected client (used by the API)."""
    client = _clients.get(account_id)
    if client is None:
        return ""
    try:
        entity = await client.get_entity(telegram_id)
        return getattr(entity, "title", "") or ""
    except Exception:
        return ""


async def account_identity(account_id: int) -> dict:
    """Basic identity of the connected account, to confirm which user is live."""
    client = _clients.get(account_id)
    if client is None or not client.is_connected():
        return {}
    try:
        me = await client.get_me()
    except Exception:
        return {}
    return {
        "id": me.id,
        "username": me.username or "",
        "first_name": me.first_name or "",
        "phone": me.phone or "",
        "is_bot": bool(me.bot),
    }


async def can_access_group(account_id: int, telegram_id: int) -> tuple[bool, str]:
    """Check whether the client can resolve a group, returning the reason if not."""
    client = _clients.get(account_id)
    if client is None:
        return False, "account not connected"
    try:
        await client.get_entity(telegram_id)
        return True, ""
    except Exception as exc:
        return False, str(exc)


async def list_dialogs(account_id: int) -> list[dict]:
    """List the groups/channels the connected account is a member of.

    Used by the admin UI to pick real group ids, and to confirm the userbot is
    actually a member of a group it is expected to watch.
    """
    client = _clients.get(account_id)
    if client is None:
        raise ValueError("Account is not connected")
    dialogs = await client.get_dialogs()
    result = []
    for dialog in dialogs:
        entity = dialog.entity
        if not (getattr(entity, "megagroup", False) or getattr(entity, "broadcast", False) or dialog.is_group):
            continue
        result.append(
            {
                "id": dialog.id,
                "title": getattr(entity, "title", "") or "",
                "is_channel": bool(getattr(entity, "broadcast", False)),
                "is_group": bool(dialog.is_group),
            }
        )
    return result
