"""
SSE — tempo real (#264).

GET /v1/events/stream — `text/event-stream`, autenticado por JWT (Bearer ou query `token`).

**Gunicorn / produção:** cada worker mantém filas in-process (v1). Com `--workers N`,
conexões SSE e pub/sub ficam isoladas por processo — ver `docs/REALTIME_SSE.md`.

Presença online grava heartbeat no Postgres a cada ping (funciona com N workers).
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.core.auth import obter_atendente_sse
from app.database import SessionLocal
from app.models.atendente import Atendente
from app.services.presenca import tocar_presenca
from app.services.realtime_hub import channel_atendente, stream_channel_events

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"])


def _presence_tick_sync(atendente_id: int) -> None:
    db = SessionLocal()
    try:
        tocar_presenca(db, atendente_id)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Falha ao gravar presença do atendente %s", atendente_id)
        raise
    finally:
        db.close()


@router.get("/stream")
async def events_stream(
    request: Request,
    atendente: Atendente = Depends(obter_atendente_sse),
):
    channel = channel_atendente(atendente.id)
    atendente_id = atendente.id
    initial = {
        "type": "connected",
        "payload": {
            "atendente_id": atendente_id,
            "canal": channel,
        },
    }

    async def on_presence_tick() -> None:
        await asyncio.to_thread(_presence_tick_sync, atendente_id)

    async def generate():
        async for chunk in stream_channel_events(
            channel,
            initial_payload=initial,
            disconnect_check=request.is_disconnected,
            on_presence_tick=on_presence_tick,
        ):
            yield chunk

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
