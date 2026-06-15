"""Pub/sub in-process para SSE (v1). Redis opcional em v2 para multi-worker Gunicorn."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Any, AsyncIterator

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL_SEC = 30
_DISCONNECT_POLL_SEC = 1.0


def channel_atendente(atendente_id: int) -> str:
    return f"atendente:{atendente_id}"


class RealtimeHub:
    """Hub in-memory: um canal por atendente, filas asyncio por conexão SSE."""

    def __init__(self) -> None:
        self._queues: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def subscribe(self, channel: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=256)
        async with self._lock:
            self._queues[channel].add(queue)
        return queue

    async def unsubscribe(self, channel: str, queue: asyncio.Queue) -> None:
        async with self._lock:
            subs = self._queues.get(channel)
            if not subs:
                return
            subs.discard(queue)
            if not subs:
                del self._queues[channel]

    async def publish(
        self,
        channel: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        envelope = {"type": event_type, "payload": payload or {}}
        async with self._lock:
            subs = list(self._queues.get(channel, ()))
        for queue in subs:
            try:
                queue.put_nowait(envelope)
            except asyncio.QueueFull:
                logger.warning(
                    "Fila SSE cheia no canal %s; evento %s descartado",
                    channel,
                    event_type,
                )


hub = RealtimeHub()


def format_sse(data: dict[str, Any]) -> str:
    body = json.dumps(data, ensure_ascii=False)
    return f"event: message\ndata: {body}\n\n"


async def stream_channel_events(
    channel: str,
    *,
    initial_payload: dict[str, Any] | None = None,
    disconnect_check: Any | None = None,
) -> AsyncIterator[str]:
    """Gera linhas SSE para um canal, com heartbeat e desconexão limpa."""
    queue = await hub.subscribe(channel)
    try:
        if initial_payload is not None:
            yield format_sse(initial_payload)
        elapsed = 0.0
        while True:
            if disconnect_check is not None and await disconnect_check():
                break
            try:
                envelope = await asyncio.wait_for(queue.get(), timeout=_DISCONNECT_POLL_SEC)
                yield format_sse(envelope)
                elapsed = 0.0
            except asyncio.TimeoutError:
                elapsed += _DISCONNECT_POLL_SEC
                if elapsed >= HEARTBEAT_INTERVAL_SEC:
                    yield format_sse({"type": "ping", "payload": {}})
                    elapsed = 0.0
    finally:
        await hub.unsubscribe(channel, queue)


async def publish_to_atendente(
    atendente_id: int,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> None:
    """Publica evento no canal do atendente (RT-F2/F3)."""
    await hub.publish(channel_atendente(atendente_id), event_type, payload)
