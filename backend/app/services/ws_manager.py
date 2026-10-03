import asyncio
import json
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """In-process pub/sub for browser WebSocket clients.

    Broadcasts are fire-and-forget: a slow or dead client is dropped rather than
    blocking the pipeline that produced the event. For multi-worker deployments a
    shared broker (Redis pub/sub) would replace the in-memory set.
    """

    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)

    @property
    def count(self) -> int:
        return len(self._clients)

    async def broadcast(self, event_type: str, payload: Any) -> None:
        message = json.dumps({"type": event_type, "data": payload}, default=str, ensure_ascii=False)
        async with self._lock:
            targets = list(self._clients)
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._clients.discard(ws)


manager = ConnectionManager()


def publish(event_type: str, payload: Any) -> None:
    """Schedule a broadcast from synchronous code (DB logging helpers).

    Uses the running loop when available; silently no-ops when called outside an
    event loop (e.g. Alembic/CLI) so logging never crashes the caller.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(manager.broadcast(event_type, payload))
