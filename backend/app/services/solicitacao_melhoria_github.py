"""GitHub Issues para solicitações de melhoria (#805 / #806)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.models.atendente import Atendente
from app.models.solicitacao_melhoria import SolicitacaoMelhoria, SolicitacaoMelhoriaComentario

logger = logging.getLogger(__name__)


def github_configurado() -> bool:
    token = (settings.GITHUB_TOKEN or "").strip()
    repo = (settings.GITHUB_REPO_SUGESTOES or "").strip()
    return bool(token and repo and "/" in repo)


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.GITHUB_TOKEN.strip()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def montar_corpo_issue(row: SolicitacaoMelhoria) -> str:
    return (
        f"## Solicitação DeskRudder #{row.id}\n\n"
        f"**Tipo:** {row.tipo}\n"
        f"**Autor:** {row.autor_nome or '—'}\n"
        f"**Organização (tenant):** {row.organizacao_id}\n"
        f"**Versão no envio:** {row.versao_contexto or '—'}\n"
        f"**Status interno:** {row.status}\n\n"
        f"### Título\n{row.titulo}\n\n"
        f"### Descrição\n{row.descricao}\n"
    )


def criar_issue(db: Session, row: SolicitacaoMelhoria, admin: Atendente) -> SolicitacaoMelhoria:
    if not github_configurado():
        raise HTTPException(
            status_code=503,
            detail="Integração GitHub não configurada (GITHUB_TOKEN / GITHUB_REPO_SUGESTOES).",
        )
    if row.github_issue_number:
        raise HTTPException(status_code=400, detail="Esta solicitação já tem issue no GitHub.")

    repo = settings.GITHUB_REPO_SUGESTOES.strip()
    url = f"https://api.github.com/repos/{repo}/issues"
    payload = {
        "title": f"[DeskRudder #{row.id}] {row.titulo}"[:240],
        "body": montar_corpo_issue(row),
        "labels": ["deskrudder-sugestao", row.tipo],
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            res = client.post(url, headers=_headers(), json=payload)
    except httpx.HTTPError as exc:
        logger.warning("GitHub create issue falhou: %s", exc)
        row.github_last_error = str(exc)
        db.add(row)
        db.commit()
        db.refresh(row)
        raise HTTPException(status_code=502, detail="Falha ao contactar o GitHub. Tente novamente.") from exc

    if res.status_code >= 400:
        row.github_last_error = (res.text or "")[:2000]
        db.add(row)
        db.commit()
        db.refresh(row)
        raise HTTPException(status_code=502, detail="GitHub rejeitou a criação da issue. Pode tentar de novo.")

    data = res.json()
    row.github_repo = repo
    row.github_issue_number = int(data["number"])
    row.github_issue_url = data.get("html_url")
    row.github_last_error = None
    row.github_last_sync_at = datetime.now(timezone.utc)
    db.add(row)
    db.add(
        SolicitacaoMelhoriaComentario(
            solicitacao_id=row.id,
            corpo=f"Issue GitHub criada: #{row.github_issue_number}",
            publico_cliente=False,
            origem="github",
            autor_atendente_id=admin.id,
            autor_nome=admin.nome,
        )
    )
    db.commit()
    db.refresh(row)
    return row


def sincronizar_issue(db: Session, row: SolicitacaoMelhoria, admin: Atendente) -> SolicitacaoMelhoria:
    """Lê o estado da issue e regista comentário interno (#806) — nunca publica ao cliente."""
    if not github_configurado():
        raise HTTPException(
            status_code=503,
            detail="Integração GitHub não configurada (GITHUB_TOKEN / GITHUB_REPO_SUGESTOES).",
        )
    if not row.github_issue_number or not row.github_repo:
        raise HTTPException(status_code=400, detail="Solicitação sem issue GitHub vinculada.")

    url = f"https://api.github.com/repos/{row.github_repo}/issues/{row.github_issue_number}"
    try:
        with httpx.Client(timeout=30.0) as client:
            res = client.get(url, headers=_headers())
    except httpx.HTTPError as exc:
        row.github_last_error = str(exc)
        db.add(row)
        db.commit()
        raise HTTPException(status_code=502, detail="Falha ao sincronizar com o GitHub.") from exc

    if res.status_code >= 400:
        row.github_last_error = (res.text or "")[:2000]
        db.add(row)
        db.commit()
        raise HTTPException(status_code=502, detail="GitHub rejeitou a sincronização.")

    data = res.json()
    state = data.get("state", "unknown")
    labels = [lb.get("name") for lb in (data.get("labels") or []) if isinstance(lb, dict)]
    label_txt = ", ".join(labels) if labels else "—"
    corpo = (
        f"Sync GitHub #{row.github_issue_number}: estado={state}; labels={label_txt}. "
        f"(Conteúdo interno — não visível ao cliente.)"
    )
    db.add(
        SolicitacaoMelhoriaComentario(
            solicitacao_id=row.id,
            corpo=corpo,
            publico_cliente=False,
            origem="github",
            autor_atendente_id=admin.id,
            autor_nome=admin.nome,
        )
    )
    row.github_last_sync_at = datetime.now(timezone.utc)
    row.github_last_error = None
    # Sugestão opcional de status (#806) — só regista nota, não muda sozinho.
    if state == "closed" and row.status not in ("concluida", "nao_sera_desenvolvida"):
        db.add(
            SolicitacaoMelhoriaComentario(
                solicitacao_id=row.id,
                corpo="Sugestão: issue GitHub fechada — considere marcar a solicitação como concluída.",
                publico_cliente=False,
                origem="github",
                autor_atendente_id=admin.id,
                autor_nome=admin.nome,
            )
        )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
