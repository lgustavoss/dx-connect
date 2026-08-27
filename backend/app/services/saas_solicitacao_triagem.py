"""Triagem no control-plane e retorno autenticado à instância (#856)."""

from __future__ import annotations

import json
import logging
import re
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
    SaasSolicitacaoGithubUpdate,
    SaasSolicitacaoImplementar,
    SaasSolicitacaoStatusUpdate,
    SaasSolicitacaoSyncComentario,
    SaasSolicitacaoSyncItem,
    SaasSolicitacaoSyncResponse,
    SaasSolicitacaoVersaoAlvoUpdate,
)
from app.services import saas_solicitacao_ingest as ingest
from app.services.solicitacao_melhoria import (
    aplicar_comentario_origem_saas,
    aplicar_protocolo_origem_saas,
    aplicar_status_origem_saas,
    aplicar_versao_alvo_origem_saas,
)
from app.services.solicitacao_melhoria_copy import normalizar_versao_alvo, validar_transicao_status

logger = logging.getLogger(__name__)

CACHE_CHAVE_PULL = "saas_triagem_pull"

_GH_ISSUE = re.compile(r"github\.com/([^/\s]+)/([^/\s]+)/issues/(\d+)", re.I)


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _deve_aplicar_local(row: SaasSolicitacaoProduto) -> bool:
    return bool(settings.SAAS_CONTROL_PLANE) and row.instance_slug == ingest.instance_slug_local()


def _tem_vinculo_github(row: SaasSolicitacaoProduto) -> bool:
    return bool(row.github_issue_number and (row.github_issue_url or "").strip())


def _aplicar_status_no_row(
    db: Session,
    row: SaasSolicitacaoProduto,
    ops: Atendente,
    *,
    status_novo: str,
    motivo_nao_desenvolvimento: str | None,
) -> SaasSolicitacaoProduto:
    """Valida transição (#953/#954), grava status e propaga à instância local. Sem commit."""
    validar_transicao_status(
        row.status,
        status_novo,
        tem_vinculo_github=_tem_vinculo_github(row),
        motivo_nao_desenvolvimento=motivo_nao_desenvolvimento,
    )
    row.status = status_novo
    if status_novo == "nao_sera_desenvolvida":
        row.motivo_nao_desenvolvimento = (motivo_nao_desenvolvimento or "").strip()
    row.triagem_atualizada_em = _agora()
    db.add(row)
    db.flush()
    if _deve_aplicar_local(row):
        aplicar_protocolo_origem_saas(db, row.origem_solicitacao_id, row.protocolo)
        aplicar_versao_alvo_origem_saas(db, row.origem_solicitacao_id, row.versao_alvo)
        aplicar_status_origem_saas(
            db,
            row.origem_solicitacao_id,
            status_novo=row.status,
            motivo_nao_desenvolvimento=row.motivo_nao_desenvolvimento,
            atendente_id=ops.id,
        )
    return row


def alterar_status(
    db: Session,
    solicitacao_id: int,
    ops: Atendente,
    data: SaasSolicitacaoStatusUpdate,
) -> SaasSolicitacaoDetalhe:
    row = ingest.obter(db, solicitacao_id)
    _aplicar_status_no_row(
        db,
        row,
        ops,
        status_novo=data.status,
        motivo_nao_desenvolvimento=data.motivo_nao_desenvolvimento,
    )
    db.commit()
    return ingest.detalhe(db, ingest.obter(db, row.id))


def implementar(
    db: Session,
    solicitacao_id: int,
    ops: Atendente,
    data: SaasSolicitacaoImplementar,
) -> SaasSolicitacaoDetalhe:
    """G2: garante issue GitHub e avança planejada → em_desenvolvimento."""
    row = ingest.obter(db, solicitacao_id)
    if row.status != "planejada":
        raise HTTPException(
            status_code=400,
            detail="Só é possível implementar a partir do status Planejada",
        )
    url = (data.github_issue_url or "").strip()
    if url or data.github_issue_number is not None:
        # Liga (ou re-liga) antes de avançar — sem commit intermediário.
        _gravar_github(db, row, data)
    elif not _tem_vinculo_github(row):
        if not data.criar_issue:
            raise HTTPException(
                status_code=400,
                detail="Indique a URL/número da issue ou permita criar no GitHub",
            )
        from app.services.saas_solicitacao_github import criar_issue_saas

        criar_issue_saas(db, row, ops)
        row = ingest.obter(db, solicitacao_id)
    _aplicar_status_no_row(
        db,
        row,
        ops,
        status_novo="em_desenvolvimento",
        motivo_nao_desenvolvimento=None,
    )
    db.commit()
    return ingest.detalhe(db, ingest.obter(db, row.id))


def definir_versao_alvo(
    db: Session,
    solicitacao_id: int,
    ops: Atendente,
    data: SaasSolicitacaoVersaoAlvoUpdate,
) -> SaasSolicitacaoDetalhe:
    """G3: versão prevista/liberada visível ao cliente em planejada/em_desenvolvimento."""
    row = ingest.obter(db, solicitacao_id)
    if row.status not in ("planejada", "em_desenvolvimento"):
        raise HTTPException(
            status_code=400,
            detail="Só é possível definir versão alvo em Planejada ou Em desenvolvimento",
        )
    versao = normalizar_versao_alvo(data.versao_alvo)
    row.versao_alvo = versao
    row.triagem_atualizada_em = _agora()
    db.add(row)
    db.flush()
    if _deve_aplicar_local(row):
        aplicar_versao_alvo_origem_saas(db, row.origem_solicitacao_id, versao)
    comentario = (data.comentario_publico or "").strip()
    if comentario:
        if corpo_publico_cita_trabalho_interno(comentario):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Não envie links ou números de issue do GitHub na mensagem ao cliente. "
                    "Use comentário interno."
                ),
            )
        c = SaasSolicitacaoProdutoComentario(
            solicitacao_id=row.id,
            corpo=comentario,
            publico_cliente=True,
            autor_atendente_id=ops.id,
            autor_nome=ops.nome,
        )
        db.add(c)
        db.flush()
        if _deve_aplicar_local(row):
            aplicar_comentario_origem_saas(
                db,
                row.origem_solicitacao_id,
                corpo=c.corpo,
                origem_externa_id=f"saas:{c.id}",
                autor_nome=c.autor_nome,
            )
    db.commit()
    return ingest.detalhe(db, ingest.obter(db, row.id))


def _gravar_github(
    db: Session,
    row: SaasSolicitacaoProduto,
    data: SaasSolicitacaoGithubUpdate | SaasSolicitacaoImplementar,
) -> None:
    """Persiste vínculo GitHub no pedido + grupo. Sem commit."""
    url = (data.github_issue_url or "").strip()
    number = data.github_issue_number
    repo = (data.github_repo or "").strip() or None
    if url:
        m = _GH_ISSUE.search(url)
        if not m:
            raise HTTPException(status_code=400, detail="URL de issue GitHub inválido")
        repo = f"{m.group(1)}/{m.group(2)}"
        number = int(m.group(3))
        url = f"https://github.com/{repo}/issues/{number}"
    elif number is not None:
        from app.services.saas_solicitacao_github import github_repo_produto

        repo = repo or github_repo_produto()
        url = f"https://github.com/{repo}/issues/{int(number)}"
    else:
        raise HTTPException(status_code=400, detail="Indique o URL ou o número da issue")
    row.github_repo = repo
    row.github_issue_number = int(number)
    row.github_issue_url = url
    db.add(row)
    from app.services import saas_solicitacao_grupo as grupo

    grupo.aplicar_github_no_grupo(
        db,
        row,
        repo=repo,
        number=int(number),
        url=url,
    )
    db.flush()


_INTERNO_NO_CLIENTE_RE = re.compile(
    r"(?i)(github\.com|/\s*issues/\d+|\bgithub\b|\bissues?\s*#\s*\d+)",
)


def corpo_publico_cita_trabalho_interno(corpo: str) -> bool:
    """GitHub / issue #N não pode ir na mensagem que o cliente vê."""
    return bool(_INTERNO_NO_CLIENTE_RE.search(corpo or ""))


def adicionar_comentario(
    db: Session,
    solicitacao_id: int,
    ops: Atendente,
    data: SaasSolicitacaoComentarioCreate,
) -> SaasSolicitacaoDetalhe:
    corpo = data.corpo.strip()
    publico = bool(data.publico_cliente)
    if publico and corpo_publico_cita_trabalho_interno(corpo):
        raise HTTPException(
            status_code=400,
            detail=(
                "Não envie links ou números de issue do GitHub na mensagem ao cliente. "
                "Use comentário interno."
            ),
        )
    row = ingest.obter(db, solicitacao_id)
    comentario = SaasSolicitacaoProdutoComentario(
        solicitacao_id=row.id,
        corpo=corpo,
        publico_cliente=publico,
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


def ligar_issue_github(
    db: Session,
    solicitacao_id: int,
    data: SaasSolicitacaoGithubUpdate,
) -> SaasSolicitacaoDetalhe:
    """Grava a issue no pedido SaaS. O cliente da instância não vê o GitHub."""
    row = ingest.obter(db, solicitacao_id)
    _gravar_github(db, row, data)
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
        protocolo=row.protocolo,
        versao_alvo=row.versao_alvo,
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
    aplicar_protocolo_origem_saas(db, item.origem_solicitacao_id, item.protocolo)
    aplicar_versao_alvo_origem_saas(db, item.origem_solicitacao_id, item.versao_alvo)
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
