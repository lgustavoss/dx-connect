"""Operação — timeline 360 e saúde do cliente da carteira (#912 / #914).

Endpoints de leitura, derivados das tabelas de CRM, comercial, implantação e
suporte. RBAC: `crm.ver` (a operação vê a carteira com o mesmo perfil do CRM).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import exigir_permissao
from app.database import get_db
from app.models.atendente import Atendente
from app.schemas.lista_paginada import ListaPaginada
from app.schemas.operacao_timeline import (
    EventoTimelineRead,
    SaudeEmpresaRead,
    SaudeStatus,
)
from app.services import operacao_timeline as svc

router = APIRouter(prefix="/operacao", tags=["operacao"])

_MAX_CARTEIRA_PAGE = 100
_DEFAULT_CARTEIRA_PAGE = 20
_MAX_TIMELINE_PAGE = 200
_DEFAULT_TIMELINE_PAGE = 50


class OrdemTimeline(str, Enum):
    asc = "asc"
    desc = "desc"


@router.get("/timeline", response_model=ListaPaginada[EventoTimelineRead])
def timeline_cliente(
    empresa_id: int = Query(..., ge=1, description="Empresa da carteira (obrigatório)"),
    categorias: list[str] | None = Query(
        None,
        description=(
            "Filtra categorias (crm, implantacao, suporte). Aceita parâmetro repetido "
            "ou separado por vírgula."
        ),
    ),
    de: datetime | None = Query(None, description="Início do período (inclusive)"),
    ate: datetime | None = Query(None, description="Fim do período (inclusive)"),
    ordem: OrdemTimeline = Query(
        OrdemTimeline.desc,
        description="desc = mais recente primeiro; asc = ordem cronológica crescente",
    ),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_TIMELINE_PAGE, ge=1, le=_MAX_TIMELINE_PAGE),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("crm.ver")),
):
    """Eventos derivados da jornada do cliente da carteira, paginados."""
    categorias_norm = svc.normalizar_categorias(categorias)
    _, eventos, total = svc.timeline_empresa(
        db,
        empresa_id=empresa_id,
        tenant_id=atendente.tenant_id,
        categorias=categorias_norm,
        de=de,
        ate=ate,
        ordem=ordem.value,
        offset=offset,
        limit=limit,
    )
    return ListaPaginada[EventoTimelineRead](items=eventos, total=total)


@router.get("/carteira", response_model=ListaPaginada[SaudeEmpresaRead])
def listar_carteira(
    busca: str | None = Query(
        None,
        description="Nome, razão social, nome fantasia ou CNPJ/CPF (só dígitos)",
    ),
    status: SaudeStatus | None = Query(
        None,
        description="Filtra pelo status de saúde (saudavel, atencao, risco)",
    ),
    incluir_inativos: bool = Query(False, description="Incluir empresas inativas"),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_CARTEIRA_PAGE, ge=1, le=_MAX_CARTEIRA_PAGE),
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("crm.ver")),
):
    """Empresas da carteira com status de saúde/engajamento e sinais objetivos."""
    itens, total = svc.listar_carteira(
        db,
        tenant_id=atendente.tenant_id,
        busca=busca,
        status_filtro=status,
        incluir_inativos=incluir_inativos,
        offset=offset,
        limit=limit,
    )
    return ListaPaginada[SaudeEmpresaRead](items=itens, total=total)


@router.get("/carteira/{empresa_id}", response_model=SaudeEmpresaRead)
def obter_saude_cliente(
    empresa_id: int,
    db: Session = Depends(get_db),
    atendente: Atendente = Depends(exigir_permissao("crm.ver")),
):
    """Saúde de uma empresa da carteira, com os sinais e a explicação dos cortes."""
    return svc.saude_da_empresa_por_id(
        db,
        empresa_id=empresa_id,
        tenant_id=atendente.tenant_id,
    )
