from datetime import date
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import or_, nullslast
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import AuditLog
from app.models.atendente import Atendente
from app.core.ordenacao_lista import OrdemLista, expr_ordem
from app.schemas.audit_log import AuditLogRead
from app.schemas.lista_paginada import ListaPaginada
from app.core.auth import exigir_admin
from app.services.audit_export import exportar_audit_csv
from app.services.ticket_dashboard_filters import period_bounds, resolve_period

router = APIRouter(prefix="/audit", tags=["audit"])

_MAX_PAGE = 100
_DEFAULT_PAGE = 20


class OrdenarAuditPor(str, Enum):
    created_at = "created_at"
    entity_type = "entity_type"
    entity_id = "entity_id"
    action = "action"
    atendente = "atendente"


def _audit_para_read(r: AuditLog) -> AuditLogRead:
    return AuditLogRead(
        id=r.id,
        entity_type=r.entity_type,
        entity_id=r.entity_id,
        action=r.action,
        atendente_id=r.atendente_id,
        atendente_nome=r.atendente.nome if r.atendente else None,
        payload_json=r.payload_json,
        ip_address=r.ip_address,
        user_agent=r.user_agent,
        request_id=r.request_id,
        created_at=r.created_at,
    )


@router.get("", response_model=ListaPaginada[AuditLogRead])
def listar_audit(
    entity_type: str | None = Query(None, description="Filtrar por tipo de entidade"),
    entity_id: int | None = Query(None, description="Filtrar por ID do registro"),
    action: str | None = Query(None, description="Filtrar por ação (assign, transfer, close, …)"),
    atendente_id: int | None = Query(None, ge=1, description="Filtrar por atendente autor"),
    de: date | None = Query(None, description="Data inicial (inclusiva)"),
    ate: date | None = Query(None, description="Data final (inclusiva)"),
    busca: str | None = Query(None, description="Tipo, ação, request_id ou nome do atendente"),
    format: str | None = Query(None, alias="format"),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    ordenar_por: OrdenarAuditPor | None = Query(None),
    ordem: OrdemLista = Query(OrdemLista.asc),
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    de_dt = ate_dt = None
    if de is not None or ate is not None:
        inicio, fim = resolve_period(de, ate)
        de_dt, ate_dt = period_bounds(inicio, fim)

    if format == "csv":
        conteudo = exportar_audit_csv(
            db,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            atendente_id=atendente_id,
            busca=busca,
            de_dt=de_dt,
            ate_dt=ate_dt,
        )
        nome = f"auditoria-{date.today().isoformat()}.csv"
        return PlainTextResponse(
            content=conteudo,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{nome}"'},
        )
    if format is not None:
        raise HTTPException(status_code=422, detail="format suportado: csv")

    q = db.query(AuditLog).options(joinedload(AuditLog.atendente))
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
    total = q.count()
    if ordenar_por is None:
        order_cols = [AuditLog.created_at.desc(), AuditLog.id.desc()]
    else:
        if ordenar_por == OrdenarAuditPor.atendente:
            q = q.outerjoin(AuditLog.atendente)
            primary = nullslast(expr_ordem(Atendente.nome, ordem))
        elif ordenar_por == OrdenarAuditPor.created_at:
            primary = expr_ordem(AuditLog.created_at, ordem)
        elif ordenar_por == OrdenarAuditPor.entity_type:
            primary = expr_ordem(AuditLog.entity_type, ordem)
        elif ordenar_por == OrdenarAuditPor.entity_id:
            primary = expr_ordem(AuditLog.entity_id, ordem)
        else:
            primary = expr_ordem(AuditLog.action, ordem)
        order_cols = [primary, expr_ordem(AuditLog.id, ordem)]
    rows = q.order_by(*order_cols).offset(offset).limit(limit).all()
    return ListaPaginada(items=[_audit_para_read(r) for r in rows], total=total)
