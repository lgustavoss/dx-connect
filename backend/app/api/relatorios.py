from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.core.auth import exigir_admin
from app.database import get_db
from app.models.atendente import Atendente
from app.schemas.relatorio import RelatorioTicketsResponse
from app.services.relatorio_tickets import (
    PREVIEW_LIMIT,
    exportar_relatorio_tickets_csv,
    listar_relatorio_tickets,
)
from app.services.ticket_dashboard_filters import normalizar_prioridade

router = APIRouter(prefix="/relatorios", tags=["relatorios"])


def _parse_prioridade(prioridade: str | None) -> str | None:
    if prioridade is None:
        return None
    try:
        return normalizar_prioridade(prioridade)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/tickets",
    summary="Relatório tabular de tickets (pré-visualização ou CSV)",
    description="Lista paginada de tickets no período (mesmos filtros do dashboard). "
    "Admin-only. Use `format=csv` para exportação (UTF-8 BOM, até 50k linhas).",
)
def relatorio_tickets(
    de: date | None = Query(None),
    ate: date | None = Query(None),
    rede_id: int | None = Query(None, ge=1),
    setor_id: int | None = Query(None, ge=1),
    prioridade: str | None = Query(None),
    format: str | None = Query(None, alias="format"),
    offset: int = Query(0, ge=0),
    limit: int = Query(PREVIEW_LIMIT, ge=1, le=PREVIEW_LIMIT),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    prio = _parse_prioridade(prioridade)
    if format == "csv":
        conteudo = exportar_relatorio_tickets_csv(
            db,
            atendente,
            de=de,
            ate=ate,
            rede_id=rede_id,
            setor_id=setor_id,
            prioridade=prio,
        )
        nome = f"relatorio-tickets-{date.today().isoformat()}.csv"
        return PlainTextResponse(
            content=conteudo,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{nome}"'},
        )
    if format is not None:
        raise HTTPException(status_code=422, detail="format suportado: csv")
    return listar_relatorio_tickets(
        db,
        atendente,
        de=de,
        ate=ate,
        rede_id=rede_id,
        setor_id=setor_id,
        prioridade=prio,
        offset=offset,
        limit=limit,
    )
