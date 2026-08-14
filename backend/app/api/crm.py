"""API CRM — leads, funil e negociações (#322 / #336–#340)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.audit import registrar_audit
from app.core.auth import exigir_admin, exigir_comercial_ou_admin
from app.database import get_db
from app.models.atendente import Atendente
from app.models.crm import CrmNegociacaoCnpjLinha
from app.schemas.crm import (
    CrmAtividadeCreate,
    CrmAtividadeRead,
    CrmLeadCreate,
    CrmLeadRead,
    CrmLeadUpdate,
    CrmLinhaCreate,
    CrmLinhaRead,
    CrmLinhaUpdate,
    CrmMoverEstagioRequest,
    CrmNegociacaoCreate,
    CrmNegociacaoRead,
    CrmNegociacaoUpdate,
    FunilEstagioCreate,
    FunilEstagioRead,
    FunilEstagioUpdate,
)
from app.schemas.lista_paginada import ListaPaginada
from app.services import crm as svc

router = APIRouter(prefix="/crm", tags=["crm"])

_MAX_PAGE = 100
_DEFAULT_PAGE = 50


@router.get("/funil-estagios", response_model=list[FunilEstagioRead])
def listar_funil(
    incluir_inativos: bool = Query(False),
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_comercial_ou_admin),
):
    return svc.listar_estagios(db, incluir_inativos=incluir_inativos)


@router.post("/funil-estagios", response_model=FunilEstagioRead, status_code=201)
def criar_funil_estagio(
    data: FunilEstagioCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = svc.criar_estagio(db, data)
    registrar_audit(db, "crm_funil_estagio", row.id, "create", atendente.id)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/funil-estagios/{estagio_id}", response_model=FunilEstagioRead)
def atualizar_funil_estagio(
    estagio_id: int,
    data: FunilEstagioUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_admin),
):
    row = svc.obter_estagio(db, estagio_id=estagio_id, apenas_ativos=False)
    row = svc.atualizar_estagio(db, row, data)
    registrar_audit(db, "crm_funil_estagio", row.id, "update", atendente.id)
    db.commit()
    db.refresh(row)
    return row


@router.get("/leads", response_model=ListaPaginada[CrmLeadRead])
def listar_leads(
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    q: str | None = Query(None),
    responsavel_id: int | None = Query(None),
    estagio_id: int | None = Query(None),
    so_minhas: bool = Query(False, description="Filtra só leads do utilizador logado"),
    ativo: bool | None = Query(True),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_comercial_ou_admin),
):
    rows, total = svc.listar_leads(
        db,
        offset=offset,
        limit=limit,
        q=q,
        responsavel_id=responsavel_id,
        estagio_id=estagio_id,
        so_minhas=so_minhas,
        ator_id=atendente.id,
        ativo=ativo,
    )
    return ListaPaginada(items=[CrmLeadRead(**svc.lead_to_read(db, r)) for r in rows], total=total)


@router.post("/leads", response_model=CrmLeadRead, status_code=201)
def criar_lead(
    data: CrmLeadCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_comercial_ou_admin),
):
    lead = svc.criar_lead(db, data, atendente)
    registrar_audit(db, "crm_lead", lead.id, "create", atendente.id)
    db.commit()
    lead = svc.obter_lead(db, lead.id)
    return CrmLeadRead(**svc.lead_to_read(db, lead))


@router.get("/leads/{lead_id}", response_model=CrmLeadRead)
def obter_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_comercial_ou_admin),
):
    lead = svc.obter_lead(db, lead_id)
    return CrmLeadRead(**svc.lead_to_read(db, lead))


@router.patch("/leads/{lead_id}", response_model=CrmLeadRead)
def atualizar_lead(
    lead_id: int,
    data: CrmLeadUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_comercial_ou_admin),
):
    lead = svc.obter_lead(db, lead_id)
    lead = svc.atualizar_lead(db, lead, data)
    registrar_audit(db, "crm_lead", lead.id, "update", atendente.id)
    db.commit()
    lead = svc.obter_lead(db, lead.id)
    return CrmLeadRead(**svc.lead_to_read(db, lead))


@router.get("/negociacoes", response_model=ListaPaginada[CrmNegociacaoRead])
def listar_negociacoes(
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    lead_id: int | None = Query(None),
    responsavel_id: int | None = Query(None),
    estagio_id: int | None = Query(None),
    ativa: bool | None = Query(True),
    q: str | None = Query(None),
    so_minhas: bool = Query(False),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_comercial_ou_admin),
):
    rows, total = svc.listar_negociacoes(
        db,
        offset=offset,
        limit=limit,
        lead_id=lead_id,
        responsavel_id=responsavel_id,
        estagio_id=estagio_id,
        ativa=ativa,
        q=q,
        so_minhas=so_minhas,
        ator_id=atendente.id,
    )
    return ListaPaginada(
        items=[CrmNegociacaoRead(**svc.negociacao_to_read(r)) for r in rows],
        total=total,
    )


@router.post("/negociacoes", response_model=CrmNegociacaoRead, status_code=201)
def criar_negociacao(
    data: CrmNegociacaoCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_comercial_ou_admin),
):
    neg = svc.criar_negociacao(db, data, atendente)
    registrar_audit(db, "crm_negociacao", neg.id, "create", atendente.id)
    db.commit()
    neg = svc.obter_negociacao(db, neg.id)
    return CrmNegociacaoRead(**svc.negociacao_to_read(neg))


@router.get("/negociacoes/{negociacao_id}", response_model=CrmNegociacaoRead)
def obter_negociacao(
    negociacao_id: int,
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_comercial_ou_admin),
):
    neg = svc.obter_negociacao(db, negociacao_id)
    return CrmNegociacaoRead(**svc.negociacao_to_read(neg))


@router.patch("/negociacoes/{negociacao_id}", response_model=CrmNegociacaoRead)
def atualizar_negociacao(
    negociacao_id: int,
    data: CrmNegociacaoUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_comercial_ou_admin),
):
    neg = svc.obter_negociacao(db, negociacao_id)
    neg = svc.atualizar_negociacao(db, neg, data)
    registrar_audit(db, "crm_negociacao", neg.id, "update", atendente.id)
    db.commit()
    neg = svc.obter_negociacao(db, neg.id)
    return CrmNegociacaoRead(**svc.negociacao_to_read(neg))


@router.post("/negociacoes/{negociacao_id}/mover-estagio", response_model=CrmNegociacaoRead)
def mover_estagio(
    negociacao_id: int,
    body: CrmMoverEstagioRequest,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_comercial_ou_admin),
):
    neg = svc.obter_negociacao(db, negociacao_id)
    neg = svc.mover_estagio(
        db,
        neg,
        ator=atendente,
        estagio_id=body.estagio_id,
        estagio_slug=body.estagio_slug,
        nota=body.nota,
    )
    registrar_audit(db, "crm_negociacao", neg.id, "mover_estagio", atendente.id)
    db.commit()
    neg = svc.obter_negociacao(db, neg.id)
    return CrmNegociacaoRead(**svc.negociacao_to_read(neg))


@router.post(
    "/negociacoes/{negociacao_id}/linhas",
    response_model=CrmLinhaRead,
    status_code=201,
)
def adicionar_linha(
    negociacao_id: int,
    data: CrmLinhaCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_comercial_ou_admin),
):
    neg = svc.obter_negociacao(db, negociacao_id)
    linha = svc.add_linha(db, neg, data)
    registrar_audit(db, "crm_negociacao_linha", linha.id, "create", atendente.id)
    db.commit()
    db.refresh(linha)
    return linha


@router.patch("/negociacoes/{negociacao_id}/linhas/{linha_id}", response_model=CrmLinhaRead)
def atualizar_linha(
    negociacao_id: int,
    linha_id: int,
    data: CrmLinhaUpdate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_comercial_ou_admin),
):
    linha = (
        db.query(CrmNegociacaoCnpjLinha)
        .filter(CrmNegociacaoCnpjLinha.id == linha_id, CrmNegociacaoCnpjLinha.negociacao_id == negociacao_id)
        .first()
    )
    if not linha:
        raise HTTPException(status_code=404, detail="Linha CNPJ não encontrada.")
    linha = svc.atualizar_linha(db, linha, data)
    registrar_audit(db, "crm_negociacao_linha", linha.id, "update", atendente.id)
    db.commit()
    db.refresh(linha)
    return linha


@router.delete("/negociacoes/{negociacao_id}/linhas/{linha_id}", status_code=204)
def excluir_linha(
    negociacao_id: int,
    linha_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_comercial_ou_admin),
):
    linha = (
        db.query(CrmNegociacaoCnpjLinha)
        .filter(CrmNegociacaoCnpjLinha.id == linha_id, CrmNegociacaoCnpjLinha.negociacao_id == negociacao_id)
        .first()
    )
    if not linha:
        raise HTTPException(status_code=404, detail="Linha CNPJ não encontrada.")
    svc.excluir_linha(db, linha)
    registrar_audit(db, "crm_negociacao_linha", linha_id, "delete", atendente.id)
    db.commit()
    return None


@router.get(
    "/negociacoes/{negociacao_id}/atividades",
    response_model=ListaPaginada[CrmAtividadeRead],
)
def listar_atividades(
    negociacao_id: int,
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_comercial_ou_admin),
):
    rows, total = svc.listar_atividades(db, negociacao_id, offset=offset, limit=limit)
    return ListaPaginada(items=rows, total=total)


@router.post(
    "/negociacoes/{negociacao_id}/atividades",
    response_model=CrmAtividadeRead,
    status_code=201,
)
def criar_atividade(
    negociacao_id: int,
    data: CrmAtividadeCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_comercial_ou_admin),
):
    row = svc.criar_atividade(db, negociacao_id, data, atendente)
    registrar_audit(db, "crm_negociacao_atividade", row.id, "create", atendente.id)
    db.commit()
    db.refresh(row)
    return row
