"""Política compartilhada de retry para filas de e-mail e HTTP (#119)."""

from __future__ import annotations

MAX_EMAIL_SEND_ATTEMPTS = 5


def retry_delay_seconds(attempt: int) -> int:
    """Backoff exponencial a partir da 1ª falha (60s, 120s, 240s… máx. 15 min)."""
    n = max(1, int(attempt))
    return min(900, 60 * (2 ** (n - 1)))


def http_retry_delay_seconds(attempt: int) -> float:
    """Backoff curto para chamadas HTTP síncronas (2s, 4s, 8s… máx. 30s)."""
    n = max(1, int(attempt))
    return min(30.0, 2.0 * (2 ** (n - 1)))


TRANSIENT_HTTP_CODES = frozenset({0, 429, 502, 503, 504})
