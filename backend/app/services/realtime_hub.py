"""Pub/sub in-process para SSE (v1). Redis opcional em v2 para multi-worker Gunicorn."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Awaitable, Callable

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL_SEC = 30
_DISCONNECT_POLL_SEC = 1.0


def channel_atendente(atendente_id: int) -> str:
    return f"atendente:{atendente_id}"


def parse_atendente_channel(channel: str) -> int | None:
    """Extrai id do canal `atendente:{id}`; None se o formato não bater."""
    if not channel.startswith("atendente:"):
        return None
    raw = channel.split(":", 1)[1]
    try:
        return int(raw)
    except ValueError:
        return None


@dataclass
class _PresenceEntry:
    online_desde: datetime
    connection_count: int


class RealtimeHub:
    """Hub in-memory: um canal por atendente, filas asyncio por conexão SSE."""

    def __init__(self) -> None:
        self._queues: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._presence: dict[int, _PresenceEntry] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, channel: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=256)
        async with self._lock:
            self._queues[channel].add(queue)
            aid = parse_atendente_channel(channel)
            if aid is not None:
                entry = self._presence.get(aid)
                if entry is None:
                    self._presence[aid] = _PresenceEntry(
                        online_desde=datetime.now(timezone.utc),
                        connection_count=1,
                    )
                else:
                    entry.connection_count += 1
        return queue

    async def unsubscribe(self, channel: str, queue: asyncio.Queue) -> None:
        async with self._lock:
            subs = self._queues.get(channel)
            if not subs:
                return
            subs.discard(queue)
            if not subs:
                del self._queues[channel]
            aid = parse_atendente_channel(channel)
            if aid is not None:
                entry = self._presence.get(aid)
                if entry is None:
                    return
                entry.connection_count -= 1
                if entry.connection_count <= 0:
                    del self._presence[aid]

    async def list_online(self) -> list[tuple[int, datetime]]:
        """Atendentes com ≥1 conexão SSE e horário de início da sessão atual."""
        async with self._lock:
            return [(aid, entry.online_desde) for aid, entry in self._presence.items()]

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
    on_presence_tick: Callable[[], Awaitable[None]] | None = None,
) -> AsyncIterator[str]:
    """Gera linhas SSE para um canal, com heartbeat e desconexão limpa."""
    queue = await hub.subscribe(channel)
    try:
        if on_presence_tick is not None:
            try:
                await on_presence_tick()
            except Exception:
                logger.exception("Falha no tick inicial de presença (%s)", channel)
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
                    if on_presence_tick is not None:
                        try:
                            await on_presence_tick()
                        except Exception:
                            logger.exception("Falha no tick de presença (%s)", channel)
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
