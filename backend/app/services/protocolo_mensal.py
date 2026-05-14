"""
Protocolos humanos mensais (#TAAAA-MM-NNNN tickets, #CAAAA-MM-NNNN chats).

Fuso de referência para YYYY-MM: America/Sao_Paulo (ver docs/PROTOCOLOS_TICKETS_CHATS.md).
"""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.protocol_sequence import ProtocolSequence

PROTOCOL_TZ = ZoneInfo("America/Sao_Paulo")


def _ano_mes_referencia(ref: datetime | None) -> str:
    tz = PROTOCOL_TZ
    dt = ref or datetime.now(tz)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc).astimezone(tz)
    else:
        dt = dt.astimezone(tz)
    return dt.strftime("%Y-%m")


def _proximo_valor(db: Session, kind: str, ano_mes: str) -> int:
    """Incrementa e devolve o próximo sequencial para (kind, ano_mes) na mesma transação."""
    if kind not in ("T", "C"):
        raise ValueError("kind deve ser T ou C")
    for _ in range(32):
        row = (
            db.query(ProtocolSequence)
            .filter(ProtocolSequence.kind == kind, ProtocolSequence.ano_mes == ano_mes)
            .with_for_update()
            .first()
        )
        if row is not None:
            row.last_value += 1
            v = row.last_value
            db.flush()
            return v
        nested = db.begin_nested()
        try:
            db.add(ProtocolSequence(kind=kind, ano_mes=ano_mes, last_value=1))
            db.flush()
            nested.commit()
            return 1
        except IntegrityError:
            nested.rollback()
            continue
    raise RuntimeError("Não foi possível obter sequência de protocolo (contenção).")


def gerar_protocolo_ticket(db: Session, *, ref: datetime | None = None) -> str:
    ano_mes = _ano_mes_referencia(ref)
    n = _proximo_valor(db, "T", ano_mes)
    return f"#T{ano_mes}-{n:04d}"


def gerar_protocolo_chat(db: Session, *, ref: datetime | None = None) -> str:
    ano_mes = _ano_mes_referencia(ref)
    n = _proximo_valor(db, "C", ano_mes)
    return f"#C{ano_mes}-{n:04d}"
