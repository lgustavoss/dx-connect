"""Triagem no control-plane e retorno autenticado à instância (#856)."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models.app_cache_meta import AppCacheMeta
from app.models.atendente import Atendente
from app.models.cliente_saas import ClienteSaaS
from app.models.saas_solicitacao_produto import SaasSolicitacaoProduto, SaasSolicitacaoProdutoComentario
from app.schemas.saas_solicitacao import (
    SaasSolicitacaoComentarioCreate,
    SaasSolicitacaoDetalhe,
    SaasSolicitacaoStatusUpdate,
    SaasSolicitacaoSyncComentario,
    SaasSolicitacaoSyncItem,
    SaasSolicitacaoSyncResponse,
)
from app.services import saas_solicitacao_ingest as ingest
from app.services.solicitacao_melhoria import aplicar_comentario_origem_saas, aplicar_status_origem_saas
from app.services.solicitacao_melhoria_copy import STATUS_VALIDOS

logger = logging.getLogger(__name__)

CACHE_CHAVE_PULL = "saas_triagem_pull"


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _deve_aplicar_local(row: SaasSolicitacaoProduto) -> bool:
    return bool(settings.SAAS_CONTROL_PLANE) and row.instance_slug == ingest.instance_slug_local()


def alterar_status(
    db: Session,
    solicitacao_id: int,
    ops: Atendente,
    data: SaasSolicitacaoStatusUpdate,
) -> SaasSolicitacaoDetalhe:
    if data.status not in STATUS_VALIDOS:
        raise HTTPException(status_code=400, detail="Status inválido")
    if data.status == "nao_sera_desenvolvida" and not (data.motivo_nao_desenvolvimento or "").strip():
        raise HTTPException(
            status_code=400,
            detail="Informe o motivo quando marcar como não será desenvolvida",
        )
    row = ingest.obter(db, solicitacao_id)
    row.status = data.status
    if data.status == "nao_sera_desenvolvida":
        row.motivo_nao_desenvolvimento = (data.motivo_nao_desenvolvimento or "").strip()
    row.triagem_atualizada_em = _agora()
    db.add(row)
    db.flush()
    if _deve_aplicar_local(row):
        aplicar_status_origem_saas(
            db,
            row.origem_solicitacao_id,
            status_novo=row.status,
            motivo_nao_desenvolvimento=row.motivo_nao_desenvolvimento,
            atendente_id=ops.id,
        )
    db.commit()
    return ingest.detalhe(db, ingest.obter(db, row.id))


def adicionar_comentario(
    db: Session,
    solicitacao_id: int,
    ops: Atendente,
    data: SaasSolicitacaoComentarioCreate,
) -> SaasSolicitacaoDetalhe:
    row = ingest.obter(db, solicitacao_id)
    comentario = SaasSolicitacaoProdutoComentario(
        solicitacao_id=row.id,
        corpo=data.corpo.strip(),
        publico_cliente=bool(data.publico_cliente),
        autor_atendente_id=ops.id,
        autor_nome=ops.nome,
    )
    db.add(comentario)
    row.triagem_atualizada_em = _agora()
    db.add(row)
    db.flush()
    if comentario.publico_cliente and _deve_aplicar_local(row):
        aplicar_comentario_origem_saas(
            db,
            row.origem_solicitacao_id,
            corpo=comentario.corpo,
            origem_externa_id=f"saas:{comentario.id}",
            autor_nome=comentario.autor_nome,
        )
    db.commit()
    return ingest.detalhe(db, ingest.obter(db, row.id))


def payload_sync(row: SaasSolicitacaoProduto) -> SaasSolicitacaoSyncItem:
    publicos = [
        SaasSolicitacaoSyncComentario(
            id=c.id,
            corpo=c.corpo,
            autor_nome=c.autor_nome,
            created_at=c.created_at,
        )
        for c in (row.comentarios or [])
        if c.publico_cliente
    ]
    return SaasSolicitacaoSyncItem(
        origem_solicitacao_id=row.origem_solicitacao_id,
        status=row.status,
        motivo_nao_desenvolvimento=row.motivo_nao_desenvolvimento,
        comentarios_publicos=publicos,
    )


def listar_sync(
    db: Session,
    cliente: ClienteSaaS,
    *,
    since: datetime | None,
) -> SaasSolicitacaoSyncResponse:
    base = db.query(SaasSolicitacaoProduto).filter(SaasSolicitacaoProduto.instance_slug == cliente.slug)
    if since is None:
        rows = (
            base.options(joinedload(SaasSolicitacaoProduto.comentarios))
            .order_by(SaasSolicitacaoProduto.id.asc())
            .all()
        )
        return SaasSolicitacaoSyncResponse(items=[payload_sync(i) for i in rows])

    ids = {
        r.id
        for r in base.filter(SaasSolicitacaoProduto.triagem_atualizada_em >= since).all()
    }
    ids.update(
        sid
        for (sid,) in db.query(SaasSolicitacaoProdutoComentario.solicitacao_id)
        .join(SaasSolicitacaoProduto)
        .filter(
            SaasSolicitacaoProduto.instance_slug == cliente.slug,
            SaasSolicitacaoProdutoComentario.created_at >= since,
        )
        .all()
    )
    if not ids:
        return SaasSolicitacaoSyncResponse(items=[])
    rows = (
        db.query(SaasSolicitacaoProduto)
        .options(joinedload(SaasSolicitacaoProduto.comentarios))
        .filter(SaasSolicitacaoProduto.id.in_(ids))
        .order_by(SaasSolicitacaoProduto.id.asc())
        .all()
    )
    return SaasSolicitacaoSyncResponse(items=[payload_sync(i) for i in rows])


def aplicar_pacote_sync(db: Session, item: SaasSolicitacaoSyncItem) -> bool:
    """Aplica um item do GET sync na instância. Sem commit."""
    aplicado = aplicar_status_origem_saas(
        db,
        item.origem_solicitacao_id,
        status_novo=item.status,
        motivo_nao_desenvolvimento=item.motivo_nao_desenvolvimento,
        atendente_id=None,
    )
    if aplicado is None:
        return False
    for c in item.comentarios_publicos:
        aplicar_comentario_origem_saas(
            db,
            item.origem_solicitacao_id,
            corpo=c.corpo,
            origem_externa_id=f"saas:{c.id}",
            autor_nome=c.autor_nome,
        )
    return True


def sync_url_from_ingest(ingest_url: str) -> str:
    base = ingest_url.strip().rstrip("/")
    if base.endswith("/sync"):
        return base
    return f"{base}/sync"


def _get_json(url: str, token: str, timeout: int = 20) -> dict:
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        raise RuntimeError(f"HTTP {e.code}: {(body or str(e.reason))[:500]}") from e


def process_triagem_pull(db: Session) -> int:
    """Pull autenticado da triagem. No-op no control-plane (apply directo cobre o local)."""
    if settings.SAAS_CONTROL_PLANE:
        return 0
    url = (settings.SAAS_CONTROL_PLANE_INGEST_URL or "").strip()
    token = (settings.SAAS_INSTANCE_INGEST_TOKEN or "").strip()
    if not url or not token:
        return 0
    meta = db.query(AppCacheMeta).filter(AppCacheMeta.chave == CACHE_CHAVE_PULL).first()
    since = meta.atualizado_em if meta else None
    sync_url = sync_url_from_ingest(url)
    if since is not None:
        qs = urllib.parse.urlencode({"since": since.isoformat()})
        sync_url = f"{sync_url}?{qs}"
    try:
        payload = _get_json(sync_url, token)
    except Exception:
        logger.exception("Falha no pull da triagem SaaS")
        return 0
    parsed = SaasSolicitacaoSyncResponse.model_validate(payload)
    n = 0
    for item in parsed.items:
        try:
            if aplicar_pacote_sync(db, item):
                n += 1
        except HTTPException:
            logger.warning(
                "Triagem SaaS ignorada para origem_solicitacao_id=%s",
                item.origem_solicitacao_id,
            )
        except Exception:
            logger.exception(
                "Falha ao aplicar triagem SaaS origem_solicitacao_id=%s",
                item.origem_solicitacao_id,
            )
    if meta is None:
        meta = AppCacheMeta(chave=CACHE_CHAVE_PULL, atualizado_em=_agora())
        db.add(meta)
    else:
        meta.atualizado_em = _agora()
    db.flush()
    return n
