"""Limite de taxa por IP nos endpoints públicos da KB (#295)."""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request, status

from app.core.login_protection import client_ip

_MAX_REQUESTS_PER_MINUTE_PER_IP = 120
_MAX_FEEDBACK_PER_MINUTE_PER_IP = 20
_MAX_CHAT_PER_MINUTE_PER_IP = 40

_lock = Lock()
_buckets: dict[str, list[float]] = defaultdict(list)
_feedback_buckets: dict[str, list[float]] = defaultdict(list)
_chat_buckets: dict[str, list[float]] = defaultdict(list)


def check_kb_public_rate_limit(request: Request) -> None:
    ip = client_ip(request)
    now = time.monotonic()
    with _lock:
        bucket = _buckets[ip]
        bucket[:] = [t for t in bucket if now - t < 60]
        if len(bucket) >= _MAX_REQUESTS_PER_MINUTE_PER_IP:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Muitas consultas à base de conhecimento. Aguarde um minuto.",
            )
        bucket.append(now)


def check_kb_public_feedback_rate_limit(request: Request) -> None:
    ip = client_ip(request)
    now = time.monotonic()
    with _lock:
        bucket = _feedback_buckets[ip]
        bucket[:] = [t for t in bucket if now - t < 60]
        if len(bucket) >= _MAX_FEEDBACK_PER_MINUTE_PER_IP:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Muitas avaliações em pouco tempo. Aguarde um minuto.",
            )
        bucket.append(now)


def check_kb_public_chat_rate_limit(request: Request) -> None:
    ip = client_ip(request)
    now = time.monotonic()
    with _lock:
        bucket = _chat_buckets[ip]
        bucket[:] = [t for t in bucket if now - t < 60]
        if len(bucket) >= _MAX_CHAT_PER_MINUTE_PER_IP:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Muitas mensagens no chat. Aguarde um minuto.",
            )
        bucket.append(now)
