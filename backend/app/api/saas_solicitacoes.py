"""API — ingest (instância→SaaS), fila e triagem para saas_ops (#855 / #856)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import settings
from app.core.auth import exigir_saas_ops
from app.core.ordenacao_lista import OrdemLista, expr_ordem
from app.database import get_db
from app.models.atendente import Atendente
from app.models.cliente_saas import ClienteSaaS
from app.models.saas_solicitacao_produto import SaasSolicitacaoProduto
from app.schemas.lista_paginada import ListaPaginada
from app.schemas.saas_solicitacao import (
    SaasSolicitacaoAnexoRead,
    SaasSolicitacaoComentarioCreate,
    SaasSolicitacaoDetalhe,
    SaasSolicitacaoIngest,
    SaasSolicitacaoListaItem,
    SaasSolicitacaoStatusUpdate,
    SaasSolicitacaoSyncResponse,
)
from app.services import saas_solicitacao_ingest as ingest
from app.services import saas_solicitacao_triagem as triagem

router = APIRouter(prefix="/saas", tags=["saas-solicitacoes"])

_MAX_PAGE = 100
_DEFAULT_PAGE = 20


class OrdenarSolicitacoesPor(str, Enum):
    ingested_at = "ingested_at"
    created_at_origem = "created_at_origem"
    titulo = "titulo"


def exigir_saas_control_plane() -> None:
    if not settings.SAAS_CONTROL_PLANE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Painel SaaS não disponível nesta instância",
        )


def _token_from_headers(authorization: str | None, x_token: str | None) -> str:
    if x_token and x_token.strip():
        return x_token.strip()
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return ""


@router.post("/ingest/solicitacoes", response_model=SaasSolicitacaoListaItem)
def ingest_solicitacao(
    data: SaasSolicitacaoIngest,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    authorization: str | None = Header(None),
    x_saas_instance_token: str | None = Header(None, alias="X-Saas-Instance-Token"),
):
    """Recebe cópia autenticada da instância. Sem JWT de utilizador."""
    token = _token_from_headers(authorization, x_saas_instance_token)
    cliente = ingest.autenticar_ingest(db, slug=data.instance_slug, token=token)
    row = ingest.upsert_from_payload(db, data, cliente=cliente)
    db.commit()
    db.refresh(row)
    if row.cliente is None:
        row.cliente = cliente
    return ingest.item_lista(row)


@router.post(
    "/ingest/solicitacoes/{origem_id}/media",
    response_model=SaasSolicitacaoAnexoRead,
    status_code=201,
)
async def ingest_solicitacao_media(
    origem_id: int,
    file: UploadFile = File(...),
    papel: str = Form("anexo"),
    storage_key: str = Form(...),
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    authorization: str | None = Header(None),
    x_saas_instance_token: str | None = Header(None, alias="X-Saas-Instance-Token"),
):
    """Recebe o ficheiro da instância (multipart). JSON já tem de ter sido ingerido."""
    token = _token_from_headers(authorization, x_saas_instance_token)
    cliente = ingest.autenticar_ingest_por_token(db, token)
    data = await file.read()
    row = ingest.receber_media_ingest(
        db,
        cliente=cliente,
        origem_solicitacao_id=origem_id,
        data=data,
        filename=file.filename,
        content_type=file.content_type,
        papel=papel,
        storage_key=storage_key,
    )
    db.commit()
    db.refresh(row)
    return ingest.anexo_read(row)


@router.get("/ingest/solicitacoes/sync", response_model=SaasSolicitacaoSyncResponse)
def sync_triagem(
    since: datetime | None = Query(None),
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    authorization: str | None = Header(None),
    x_saas_instance_token: str | None = Header(None, alias="X-Saas-Instance-Token"),
):
    """Pull autenticado: status + comentários públicos da triagem para a instância."""
    token = _token_from_headers(authorization, x_saas_instance_token)
    cliente = ingest.autenticar_ingest_por_token(db, token)
    return triagem.listar_sync(db, cliente, since=since)


@router.get("/solicitacoes", response_model=ListaPaginada[SaasSolicitacaoListaItem])
def listar(
    busca: str | None = Query(None),
    tipo: str | None = Query(None),
    status_filtro: str | None = Query(None, alias="status"),
    slug: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_PAGE, ge=1, le=_MAX_PAGE),
    ordenar_por: OrdenarSolicitacoesPor | None = Query(OrdenarSolicitacoesPor.ingested_at),
    ordem: OrdemLista = Query(OrdemLista.desc),
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    __: Atendente = Depends(exigir_saas_ops),
):
    q = ingest.query_base(db)
    if busca and busca.strip():
        term = f"%{busca.strip()}%"
        q = q.outerjoin(ClienteSaaS, SaasSolicitacaoProduto.cliente_saas_id == ClienteSaaS.id).filter(
            or_(
                SaasSolicitacaoProduto.titulo.ilike(term),
                SaasSolicitacaoProduto.autor_nome.ilike(term),
                SaasSolicitacaoProduto.instance_slug.ilike(term),
                ClienteSaaS.nome.ilike(term),
            )
        )
    if tipo and tipo.strip():
        q = q.filter(SaasSolicitacaoProduto.tipo == tipo.strip())
    if status_filtro and status_filtro.strip():
        q = q.filter(SaasSolicitacaoProduto.status == status_filtro.strip())
    if slug and slug.strip():
        q = q.filter(SaasSolicitacaoProduto.instance_slug == slug.strip().lower())
    total = q.count()
    if ordenar_por == OrdenarSolicitacoesPor.titulo:
        order_cols = [
            expr_ordem(SaasSolicitacaoProduto.titulo, ordem),
            expr_ordem(SaasSolicitacaoProduto.id, ordem),
        ]
    elif ordenar_por == OrdenarSolicitacoesPor.created_at_origem:
        order_cols = [
            expr_ordem(SaasSolicitacaoProduto.created_at_origem, ordem),
            expr_ordem(SaasSolicitacaoProduto.id, ordem),
        ]
    else:
        order_cols = [
            expr_ordem(SaasSolicitacaoProduto.ingested_at, ordem),
            expr_ordem(SaasSolicitacaoProduto.id, ordem),
        ]
    items = q.order_by(*order_cols).offset(offset).limit(limit).all()
    return ListaPaginada(items=[ingest.item_lista(i) for i in items], total=total)


@router.get("/solicitacoes/{solicitacao_id}", response_model=SaasSolicitacaoDetalhe)
def obter(
    solicitacao_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    __: Atendente = Depends(exigir_saas_ops),
):
    return ingest.detalhe(db, ingest.obter(db, solicitacao_id))


@router.patch("/solicitacoes/{solicitacao_id}/status", response_model=SaasSolicitacaoDetalhe)
def alterar_status(
    solicitacao_id: int,
    data: SaasSolicitacaoStatusUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    ops: Atendente = Depends(exigir_saas_ops),
):
    return triagem.alterar_status(db, solicitacao_id, ops, data)


@router.post("/solicitacoes/{solicitacao_id}/comentarios", response_model=SaasSolicitacaoDetalhe)
def adicionar_comentario(
    solicitacao_id: int,
    data: SaasSolicitacaoComentarioCreate,
    db: Session = Depends(get_db),
    _: None = Depends(exigir_saas_control_plane),
    ops: Atendente = Depends(exigir_saas_ops),
):
    return triagem.adicionar_comentario(db, solicitacao_id, ops, data)
