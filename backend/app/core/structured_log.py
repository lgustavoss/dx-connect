"""Logs estruturados (JSON em uma linha) para auditoria operacional (#119)."""

from __future__ import annotations

import json
import logging
from typing import Any


def log_event(logger: logging.Logger, event: str, *, level: int = logging.INFO, **fields: Any) -> None:
    payload = {"event": event, **fields}
    try:
        line = json.dumps(payload, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        line = json.dumps({"event": event, "serialization_error": True}, ensure_ascii=False)
    logger.log(level, line)
