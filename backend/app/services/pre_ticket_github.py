"""GitHub Issues a partir de pré-ticket aprovado (#813)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.models.atendente import Atendente
from app.models.pre_ticket_sessao import PreTicketSessao
from app.services.solicitacao_melhoria_github import _headers, github_configurado

logger = logging.getLogger(__name__)


def _repo() -> str:
    return (settings.GITHUB_REPO_SUGESTOES or "").strip()


def montar_corpo_issue(row: PreTicketSessao, analise: dict[str, Any]) -> str:
    titulo_pub = row.rascunho_publicado_titulo or row.rascunho_titulo or "—"
    corpo_pub = row.rascunho_publicado_corpo or row.rascunho_corpo or ""
    criterios = analise.get("criterios_aceite") or []
    dependencias = analise.get("dependencias") or []
    riscos = analise.get("riscos") or []

    linhas = [
        f"## Pré-ticket DeskRudder #{row.id}",
        "",
        f"**Classificação:** {analise.get('classificacao', '—')}",
        f"**Viabilidade:** {analise.get('viabilidade', '—')}",
        f"**Prompt IA:** {row.prompt_version or '—'}",
    ]
    if row.ticket_id:
        linhas.append(f"**Ticket de origem:** #{row.ticket_id}")
    if row.aprovado_em:
        linhas.append(f"**Aprovado em:** {row.aprovado_em.isoformat()}")
    linhas.extend(["", "### Contexto", row.contexto, "", "### Problema", row.problema])
    if row.impacto:
        linhas.extend(["", "### Impacto", row.impacto])
    if criterios:
        linhas.extend(["", "### Critérios de aceite", ""])
        linhas.extend(f"- [ ] {c}" for c in criterios)
    if dependencias:
        linhas.extend(["", "### Dependências", ""])
        linhas.extend(f"- {d}" for d in dependencias)
    if riscos:
        linhas.extend(["", "### Riscos", ""])
        linhas.extend(f"- {r}" for r in riscos)
    linhas.extend(["", "### Rascunho aprovado", f"**Título:** {titulo_pub}", "", corpo_pub])
    return "\n".join(linhas)


def _post_issue(repo: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{repo}/issues"
    with httpx.Client(timeout=30.0) as client:
        res = client.post(url, headers=_headers(), json=payload)
    if res.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail="GitHub rejeitou a criação da issue. Pode tentar de novo.",
        )
    return res.json()


def criar_issue(
    db: Session,
    row: PreTicketSessao,
    admin: Atendente,
    analise: dict[str, Any],
) -> PreTicketSessao:
    if not github_configurado():
        raise HTTPException(
            status_code=503,
            detail="Integração GitHub não configurada (GITHUB_TOKEN / GITHUB_REPO_SUGESTOES).",
        )
    if row.github_issue_number:
        return row
    if row.estado != "aprovado":
        raise HTTPException(
            status_code=400,
            detail="Só é possível publicar após aprovar o rascunho.",
        )
    if not row.rascunho_titulo or not row.rascunho_corpo:
        raise HTTPException(status_code=400, detail="Rascunho incompleto para publicação.")

    repo = _repo()
    classificacao = str(analise.get("classificacao") or "melhoria")
    titulo = row.rascunho_titulo.strip()
    payload = {
        "title": f"[Pré-ticket #{row.id}] {titulo}"[:240],
        "body": montar_corpo_issue(row, analise),
        "labels": ["deskrudder-pre-ticket", classificacao],
    }
    try:
        data = _post_issue(repo, payload)
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        logger.warning("GitHub create issue pré-ticket falhou: %s", exc)
        row.github_last_error = str(exc)[:2000]
        db.add(row)
        db.commit()
        db.refresh(row)
        raise HTTPException(status_code=502, detail="Falha ao contactar o GitHub. Tente novamente.") from exc

    agora = datetime.now(timezone.utc)
    row.github_repo = repo
    row.github_issue_number = int(data["number"])
    row.github_issue_url = data.get("html_url")
    row.github_last_error = None
    row.rascunho_publicado_titulo = titulo
    row.rascunho_publicado_corpo = row.rascunho_corpo
    row.publicado_por_id = admin.id
    row.publicado_em = agora
    row.estado = "publicado"
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
