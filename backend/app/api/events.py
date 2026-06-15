"""
SSE — tempo real (#264).

GET /v1/events/stream — `text/event-stream`, autenticado por JWT (Bearer ou query `token`).

**Gunicorn / produção:** cada worker mantém filas in-process (v1). Com `--workers N`,
conexões SSE e pub/sub ficam isoladas por processo — ver `docs/REALTIME_SSE.md`.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.core.auth import obter_atendente_sse
from app.models.atendente import Atendente
from app.services.realtime_hub import channel_atendente, stream_channel_events

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/stream")
async def events_stream(
    request: Request,
    atendente: Atendente = Depends(obter_atendente_sse),
):
    channel = channel_atendente(atendente.id)
    initial = {
        "type": "connected",
        "payload": {
            "atendente_id": atendente.id,
            "canal": channel,
        },
    }

    async def generate():
        async for chunk in stream_channel_events(
            channel,
            initial_payload=initial,
            disconnect_check=request.is_disconnected,
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
