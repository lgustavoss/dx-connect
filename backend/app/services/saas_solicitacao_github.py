"""Criar/ligar issue GitHub a partir da solicitação SaaS (#954)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.models.atendente import Atendente
from app.models.saas_solicitacao_produto import SaasSolicitacaoProduto, SaasSolicitacaoProdutoComentario
from app.services.solicitacao_melhoria_github import github_configurado, _headers

logger = logging.getLogger(__name__)


def github_repo_produto() -> str:
    return (settings.GITHUB_REPO_SUGESTOES or "").strip() or "lgustavoss/dx-connect"


def montar_corpo_issue_saas(db: Session, row: SaasSolicitacaoProduto) -> str:
    from app.services import saas_solicitacao_grupo as grupo

    demanda = grupo.texto_github_demanda(db, row)
    proto = row.protocolo or f"saas-{row.id}"
    return (
        f"## Solicitação DeskRudder {proto}\n\n"
        f"**Tipo:** {row.tipo}\n"
        f"**Instância:** {row.instance_slug}\n"
        f"**Autor (origem):** {row.autor_nome or '—'}\n"
        f"**Versão no envio:** {row.versao_contexto or '—'}\n"
        f"**Status no SaaS:** {row.status}\n\n"
        f"### Demanda (grupo)\n{demanda}\n\n"
        f"### Título\n{row.titulo}\n\n"
        f"### Descrição\n{row.descricao}\n"
    )


def criar_issue_saas(
    db: Session,
    row: SaasSolicitacaoProduto,
    ops: Atendente,
) -> SaasSolicitacaoProduto:
    """Cria issue no GitHub e grava vínculo no pedido (e no grupo). Sem commit."""
    if not github_configurado():
        raise HTTPException(
            status_code=503,
            detail="Integração GitHub não configurada (GITHUB_TOKEN / GITHUB_REPO_SUGESTOES).",
        )
    if row.github_issue_number:
        raise HTTPException(status_code=400, detail="Esta solicitação já tem issue no GitHub.")

    repo = settings.GITHUB_REPO_SUGESTOES.strip()
    proto = row.protocolo or f"#{row.id}"
    url = f"https://api.github.com/repos/{repo}/issues"
    payload = {
        "title": f"[{proto}] {row.titulo}"[:240],
        "body": montar_corpo_issue_saas(db, row),
        "labels": ["deskrudder-sugestao", row.tipo],
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            res = client.post(url, headers=_headers(), json=payload)
    except httpx.HTTPError as exc:
        logger.warning("GitHub create issue (SaaS) falhou: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Falha ao contatar o GitHub. Tente novamente.",
        ) from exc

    if res.status_code >= 400:
        logger.warning("GitHub rejeitou create issue SaaS: %s", (res.text or "")[:500])
        raise HTTPException(
            status_code=502,
            detail="GitHub rejeitou a criação da issue. Pode tentar de novo.",
        )

    data = res.json()
    number = int(data["number"])
    html = data.get("html_url") or f"https://github.com/{repo}/issues/{number}"
    row.github_repo = repo
    row.github_issue_number = number
    row.github_issue_url = html
    db.add(row)
    from app.services import saas_solicitacao_grupo as grupo

    grupo.aplicar_github_no_grupo(db, row, repo=repo, number=number, url=html)
    db.add(
        SaasSolicitacaoProdutoComentario(
            solicitacao_id=row.id,
            corpo=f"Issue GitHub criada: #{number} (só ops — o cliente não vê).",
            publico_cliente=False,
            autor_atendente_id=ops.id,
            autor_nome=ops.nome,
        )
    )
    row.triagem_atualizada_em = datetime.now(timezone.utc)
    db.add(row)
    db.flush()
    return row
