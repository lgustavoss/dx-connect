"""
Protocolos humanos mensais (#TYYYYMM-NNNN tickets, #CYYYYMM-NNNN chats, #SYYYYMM-NNNN sugestões).

Fuso de referência para YYYYMM: America/Sao_Paulo (ver docs/PROTOCOLOS_TICKETS_CHATS.md).
"""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.protocol_sequence import ProtocolSequence

PROTOCOL_TZ = ZoneInfo("America/Sao_Paulo")


def _periodo_mensal_ref(ref: datetime | None) -> str:
    """Chave mensal YYYYMM (sem hífen) no fuso America/Sao_Paulo."""
    tz = PROTOCOL_TZ
    dt = ref or datetime.now(tz)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc).astimezone(tz)
    else:
        dt = dt.astimezone(tz)
    return dt.strftime("%Y%m")


def _proximo_valor(db: Session, kind: str, periodo: str) -> int:
    """Incrementa e devolve o próximo sequencial para (kind, periodo YYYYMM) na mesma transação."""
    if kind not in ("T", "C", "P", "S"):
        raise ValueError("kind deve ser T, C, P ou S")
    for _ in range(32):
        row = (
            db.query(ProtocolSequence)
            .filter(ProtocolSequence.kind == kind, ProtocolSequence.ano_mes == periodo)
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
            db.add(ProtocolSequence(kind=kind, ano_mes=periodo, last_value=1))
            db.flush()
            nested.commit()
            return 1
        except IntegrityError:
            nested.rollback()
            continue
    raise RuntimeError("Não foi possível obter sequência de protocolo (contenção).")


def gerar_protocolo_ticket(db: Session, *, ref: datetime | None = None) -> str:
    yyyymm = _periodo_mensal_ref(ref)
    n = _proximo_valor(db, "T", yyyymm)
    return f"#T{yyyymm}-{n:04d}"


def gerar_protocolo_chat(db: Session, *, ref: datetime | None = None) -> str:
    yyyymm = _periodo_mensal_ref(ref)
    n = _proximo_valor(db, "C", yyyymm)
    return f"#C{yyyymm}-{n:04d}"


def gerar_protocolo_portal(db: Session, *, ref: datetime | None = None) -> str:
    yyyymm = _periodo_mensal_ref(ref)
    n = _proximo_valor(db, "P", yyyymm)
    return f"#P{yyyymm}-{n:04d}"


def gerar_protocolo_solicitacao(db: Session, *, ref: datetime | None = None) -> str:
    yyyymm = _periodo_mensal_ref(ref)
    n = _proximo_valor(db, "S", yyyymm)
    return f"#S{yyyymm}-{n:04d}"


def normalizar_protocolo_solicitacao(raw: str | None) -> str | None:
    s = (raw or "").strip()
    if not s:
        return None
    if not s.startswith("#"):
        s = "#" + s
    if len(s) < 3:
        return s
    return "#" + s[1].upper() + s[2:]
