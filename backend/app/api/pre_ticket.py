"""API de pré-ticket com IA (#809 / #810 / #813 / #814 / #815)."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.pre_ticket_rbac import (
    exigir_pre_ticket_acesso,
    exigir_pre_ticket_analisar,
    exigir_pre_ticket_aprovar,
    exigir_pre_ticket_publicar,
)
from app.database import get_db
from app.models.atendente import Atendente
from app.schemas.pre_ticket import (
    PreTicketHistoricoItem,
    PreTicketMetricasRead,
    PreTicketRascunhoUpdate,
    PreTicketSessaoCreate,
    PreTicketSessaoListaItem,
    PreTicketSessaoRead,
)
from app.services import pre_ticket as svc
from app.services import pre_ticket_metricas as metricas_svc
from app.services.solicitacao_melhoria_github import github_configurado

router = APIRouter(prefix="/pre-ticket", tags=["pre-ticket"])


@router.get("/status")
def status_ia(_: Atendente = Depends(exigir_pre_ticket_acesso)):
    from app.services.pre_ticket_ai import pre_ticket_ia_habilitada

    return {
        "ia_habilitada": pre_ticket_ia_habilitada(),
        "github_habilitado": github_configurado(),
    }


@router.get("/metricas", response_model=PreTicketMetricasRead)
def obter_metricas(
    desde: datetime | None = Query(None),
    ate: datetime | None = Query(None),
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_pre_ticket_acesso),
):
    return metricas_svc.montar_relatorio(db, svc.tenant_id(admin), desde=desde, ate=ate)


@router.get("/sessoes", response_model=list[PreTicketSessaoListaItem])
def listar_sessoes(
    limite: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_pre_ticket_acesso),
):
    rows = svc.listar(db, svc.tenant_id(admin), limite=limite)
    return [svc.item_lista(r, db) for r in rows]


@router.post("/sessoes", response_model=PreTicketSessaoRead)
def criar_sessao(
    data: PreTicketSessaoCreate,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_pre_ticket_acesso),
):
    row = svc.criar(db, admin, data)
    return svc.serializar(row, db)


@router.get("/sessoes/{sessao_id}", response_model=PreTicketSessaoRead)
def obter_sessao(
    sessao_id: int,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_pre_ticket_acesso),
):
    row = svc.obter(db, sessao_id, svc.tenant_id(admin))
    return svc.serializar(row, db)


@router.get("/sessoes/{sessao_id}/historico", response_model=list[PreTicketHistoricoItem])
def obter_historico(
    sessao_id: int,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_pre_ticket_acesso),
):
    row = svc.obter(db, sessao_id, svc.tenant_id(admin))
    return [svc.serializar_historico(h) for h in svc.listar_historico(db, row)]


@router.patch("/sessoes/{sessao_id}/rascunho", response_model=PreTicketSessaoRead)
def editar_rascunho(
    sessao_id: int,
    data: PreTicketRascunhoUpdate,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_pre_ticket_acesso),
):
    row = svc.obter(db, sessao_id, svc.tenant_id(admin))
    row = svc.atualizar_rascunho(db, row, admin, data)
    return svc.serializar(row, db)


@router.post("/sessoes/{sessao_id}/analisar", response_model=PreTicketSessaoRead)
def analisar_sessao(
    sessao_id: int,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_pre_ticket_analisar),
):
    row = svc.obter(db, sessao_id, svc.tenant_id(admin))
    row = svc.analisar(db, row, admin)
    return svc.serializar(row, db)


@router.post("/sessoes/{sessao_id}/aprovar", response_model=PreTicketSessaoRead)
def aprovar_sessao(
    sessao_id: int,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_pre_ticket_aprovar),
):
    row = svc.obter(db, sessao_id, svc.tenant_id(admin))
    row = svc.aprovar(db, row, admin)
    return svc.serializar(row, db)


@router.post("/sessoes/{sessao_id}/github", response_model=PreTicketSessaoRead)
def publicar_github(
    sessao_id: int,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_pre_ticket_publicar),
):
    row = svc.obter(db, sessao_id, svc.tenant_id(admin))
    row = svc.publicar_github(db, row, admin)
    return svc.serializar(row, db)


@router.post("/sessoes/{sessao_id}/descartar", response_model=PreTicketSessaoRead)
def descartar_sessao(
    sessao_id: int,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_pre_ticket_acesso),
):
    row = svc.obter(db, sessao_id, svc.tenant_id(admin))
    row = svc.descartar(db, row, admin)
    return svc.serializar(row, db)
