"""Serialização por wa_id ao abrir/reutilizar chat WhatsApp (#608)."""

from __future__ import annotations

import threading

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.whatsapp_contato_match import canonical_wa_id_para_lock

_WA_LOCK_NS = 608608
_wa_thread_locks: dict[str, threading.Lock] = {}
_wa_thread_locks_guard = threading.Lock()


def _thread_lock(wa_id: str) -> threading.Lock:
    with _wa_thread_locks_guard:
        lock = _wa_thread_locks.get(wa_id)
        if lock is None:
            lock = threading.Lock()
            _wa_thread_locks[wa_id] = lock
        return lock


def lock_wa_id_para_chat(db: Session, wa_id: str) -> None:
    """
    Garante uma única criação de chat aberto por contacto.

    Usa forma canónica (DDI/nono dígito) para o mesmo contacto não passar
    por locks diferentes. PostgreSQL: advisory lock transacional; SQLite: in-process.
    """
    wa = canonical_wa_id_para_lock(wa_id)
    if not wa:
        return
    bind = db.get_bind()
    if bind.dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(:ns, hashtext(:wa_id))"),
            {"ns": _WA_LOCK_NS, "wa_id": wa},
        )
    else:
        _thread_lock(wa).acquire()


def unlock_wa_id_para_chat(db: Session, wa_id: str) -> None:
    """Liberta lock in-process (SQLite). No-op em PostgreSQL."""
    wa = canonical_wa_id_para_lock(wa_id)
    if not wa:
        return
    if db.get_bind().dialect.name != "postgresql":
        _thread_lock(wa).release()
