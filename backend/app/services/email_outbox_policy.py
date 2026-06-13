"""Política compartilhada de retry para filas de e-mail (#119)."""

from __future__ import annotations

MAX_EMAIL_SEND_ATTEMPTS = 5


def retry_delay_seconds(attempt: int) -> int:
    """Backoff exponencial a partir da 1ª falha (60s, 120s, 240s… máx. 15 min)."""
    n = max(1, int(attempt))
    return min(900, 60 * (2 ** (n - 1)))
