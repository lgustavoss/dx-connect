"""Exportação CSV da trilha de auditoria."""

from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models import AuditLog
from app.models.atendente import Atendente

MAX_EXPORT_ROWS = 50_000

_CSV_HEADERS = [
    "id",
    "created_at",
    "entity_type",
    "entity_id",
    "action",
    "atendente_id",
    "atendente_nome",
    "ip_address",
    "request_id",
    "payload_json",
]


def _apply_audit_filters(
    q,
    db: Session,
    *,
    entity_type: str | None,
    entity_id: int | None,
    action: str | None,
    atendente_id: int | None,
    busca: str | None,
    de_dt: datetime | None,
    ate_dt: datetime | None,
):
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        q = q.filter(AuditLog.entity_id == entity_id)
    if action:
        q = q.filter(AuditLog.action == action)
    if atendente_id is not None:
        q = q.filter(AuditLog.atendente_id == atendente_id)
    if de_dt is not None:
        q = q.filter(AuditLog.created_at >= de_dt)
    if ate_dt is not None:
        q = q.filter(AuditLog.created_at < ate_dt)
    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        atendente_ids = db.query(Atendente.id).filter(Atendente.nome.ilike(term))
        q = q.filter(
            or_(
                AuditLog.entity_type.ilike(term),
                AuditLog.action.ilike(term),
                AuditLog.request_id.ilike(term),
                AuditLog.atendente_id.in_(atendente_ids),
            )
        )
    return q


def exportar_audit_csv(
    db: Session,
    *,
    entity_type: str | None = None,
    entity_id: int | None = None,
    action: str | None = None,
    atendente_id: int | None = None,
    busca: str | None = None,
    de_dt: datetime | None = None,
    ate_dt: datetime | None = None,
) -> str:
    q = db.query(AuditLog).options(joinedload(AuditLog.atendente))
    q = _apply_audit_filters(
        q,
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        atendente_id=atendente_id,
        busca=busca,
        de_dt=de_dt,
        ate_dt=ate_dt,
    )
    rows = q.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(MAX_EXPORT_ROWS).all()

    buffer = io.StringIO()
    buffer.write("\ufeff")
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(_CSV_HEADERS)
    for r in rows:
        payload = json.dumps(r.payload_json, ensure_ascii=False) if r.payload_json else ""
        writer.writerow(
            [
                r.id,
                r.created_at.isoformat() if r.created_at else "",
                r.entity_type,
                r.entity_id,
                r.action,
                r.atendente_id if r.atendente_id is not None else "",
                r.atendente.nome if r.atendente else "",
                r.ip_address or "",
                r.request_id or "",
                payload,
            ]
        )
    return buffer.getvalue()
