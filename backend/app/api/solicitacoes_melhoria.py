"""API de solicitações de melhoria (#799 / #800–#807)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.auth import exigir_admin, obter_atendente_atual
from app.models.atendente import Atendente
from app.schemas.solicitacao_melhoria import (
    SolicitacaoComentarioCreate,
    SolicitacaoMelhoriaCreate,
    SolicitacaoMelhoriaListaItem,
    SolicitacaoMelhoriaRead,
    SolicitacaoMelhoriaStatusUpdate,
)
from app.services import solicitacao_melhoria as svc
from app.services import solicitacao_melhoria_github as gh_svc

router = APIRouter(prefix="/solicitacoes-melhoria", tags=["solicitacoes-melhoria"])


@router.post("", response_model=SolicitacaoMelhoriaRead)
def criar_solicitacao(
    data: SolicitacaoMelhoriaCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    row = svc.criar(db, atendente, data)
    return svc.serializar(row, incluir_github=False, incluir_internos=False)


@router.get("/minhas", response_model=list[SolicitacaoMelhoriaListaItem])
def listar_minhas(
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    rows = svc.listar_minhas(db, atendente)
    return [svc.item_lista(r, incluir_github=False) for r in rows]


@router.get("/admin", response_model=list[SolicitacaoMelhoriaListaItem])
def listar_admin(
    status: str | None = Query(None),
    tipo: str | None = Query(None),
    organizacao_id: int | None = Query(None),
    desde: datetime | None = Query(None),
    ate: datetime | None = Query(None),
    db: Session = Depends(get_db),
    _: Atendente = Depends(exigir_admin),
):
    rows = svc.listar_admin(
        db, status_filtro=status, tipo=tipo, organizacao_id=organizacao_id, desde=desde, ate=ate
    )
    return [svc.item_lista(r, incluir_github=True) for r in rows]


@router.get("/{solicitacao_id}", response_model=SolicitacaoMelhoriaRead)
def obter(
    solicitacao_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    row = svc.obter_para_leitura(db, solicitacao_id, atendente)
    admin = atendente.role == "admin"
    return svc.serializar(row, incluir_github=admin, incluir_internos=admin)


@router.patch("/{solicitacao_id}/status", response_model=SolicitacaoMelhoriaRead)
def alterar_status(
    solicitacao_id: int,
    data: SolicitacaoMelhoriaStatusUpdate,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    row = svc.alterar_status(db, solicitacao_id, admin, data)
    return svc.serializar(row, incluir_github=True, incluir_internos=True)


@router.post("/{solicitacao_id}/comentarios", response_model=SolicitacaoMelhoriaRead)
def comentar(
    solicitacao_id: int,
    data: SolicitacaoComentarioCreate,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(obter_atendente_atual),
):
    row = svc.adicionar_comentario(db, solicitacao_id, atendente, data)
    admin = atendente.role == "admin"
    return svc.serializar(row, incluir_github=admin, incluir_internos=admin)


@router.post("/{solicitacao_id}/github", response_model=SolicitacaoMelhoriaRead)
def criar_github(
    solicitacao_id: int,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    row = svc.obter_para_leitura(db, solicitacao_id, admin)
    row = gh_svc.criar_issue(db, row, admin)
    return svc.serializar(row, incluir_github=True, incluir_internos=True)


@router.post("/{solicitacao_id}/github/sincronizar", response_model=SolicitacaoMelhoriaRead)
def sync_github(
    solicitacao_id: int,
    db: Session = Depends(get_db),
    admin: Atendente = Depends(exigir_admin),
):
    row = svc.obter_para_leitura(db, solicitacao_id, admin)
    row = gh_svc.sincronizar_issue(db, row, admin)
    return svc.serializar(row, incluir_github=True, incluir_internos=True)
