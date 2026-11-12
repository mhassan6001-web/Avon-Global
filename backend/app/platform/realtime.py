"""Real-time events over WebSockets, fanned out through Redis pub/sub.

Every API worker publishes events to a per-user Redis channel; each open
WebSocket subscribes only to its own user's channel. Events carry ids and
short summaries; clients re-fetch details through the normal, permission-
checked API. Delivery is best effort: if Redis is down, the app still works
and screens refresh on their next request.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import uuid
from collections.abc import Iterable
from typing import Any
from urllib.parse import urlsplit

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis import asyncio as aioredis

from app.core.config import get_settings
from app.db import session as db_session
from app.platform import ratelimit
from app.platform.authz.deps import SESSION_COOKIE
from app.platform.identity import service as identity

log = logging.getLogger("aven.realtime")
router = APIRouter(tags=["realtime"])
REVALIDATE_SECONDS = 60


def channel(user_id: uuid.UUID | str) -> str:
    return f"aven:user:{user_id}"


def publish(user_ids: Iterable[uuid.UUID], event: dict[str, Any]) -> None:
    """Send an event to users' open sessions. Call after the change is committed."""
    payload = json.dumps(event, default=str)
    try:
        r = ratelimit.client()
        for uid in set(user_ids):
            r.publish(channel(uid), payload)
    except Exception:  # real-time delivery must never break the request
        log.warning("realtime publish failed", exc_info=True)


def _origin_allowed(origin: str | None) -> bool:
    if origin is None:  # non-browser clients (tests, CLI) send no Origin
        return True
    settings = get_settings()
    allowed = {o.rstrip("/") for o in settings.cors_origins} | {
        settings.public_base_url.rstrip("/")
    }
    parts = urlsplit(origin)
    return f"{parts.scheme}://{parts.netloc}" in allowed


def _authenticate(raw: str | None) -> uuid.UUID | None:
    if not raw:
        return None
    db = db_session.get_session_factory()()
    try:
        found = identity.find_session(db, raw)
        db.commit()
        if found is None:
            return None
        session, user = found
        if session.state != "active":
            return None
        return user.id
    finally:
        db.close()


@router.websocket("/ws")
async def events(websocket: WebSocket) -> None:
    """Authenticated, read-only event stream for the signed-in user."""
    if not _origin_allowed(websocket.headers.get("origin")):
        await websocket.close(code=4403)
        return
    raw = websocket.cookies.get(SESSION_COOKIE)
    user_id = await asyncio.to_thread(_authenticate, raw)
    if user_id is None:
        await websocket.close(code=4401)
        return
    await websocket.accept()
    redis = aioredis.from_url(get_settings().redis_url, decode_responses=True)
    pubsub = redis.pubsub()
    try:
        await pubsub.subscribe(channel(user_id))
        await websocket.send_json({"type": "ready"})

        async def forward() -> None:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("type") == "message":
                    await websocket.send_text(str(message["data"]))

        async def receive() -> None:
            while True:
                text = await websocket.receive_text()
                if text == "ping":
                    await websocket.send_json({"type": "pong"})

        async def revalidate() -> None:
            while True:
                await asyncio.sleep(REVALIDATE_SECONDS)
                if await asyncio.to_thread(_authenticate, raw) is None:
                    await websocket.close(code=4401)
                    return

        tasks = [asyncio.create_task(f()) for f in (forward, receive, revalidate)]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        for task in done:
            exc = task.exception()
            if exc and not isinstance(exc, WebSocketDisconnect):
                log.info("websocket closed: %s", type(exc).__name__)
    except WebSocketDisconnect:
        pass
    finally:
        with contextlib.suppress(Exception):
            await pubsub.unsubscribe()
            await pubsub.aclose()  # type: ignore[no-untyped-call]
            await redis.aclose()
