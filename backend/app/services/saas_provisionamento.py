"""Provisionamento de instâncias a partir do painel SaaS (#524 / DR-04)."""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.cliente_saas import ClienteSaaS
from app.services.saas_clientes import SaasErro, obter
from app.services.saas_notify import notificar_equipe_saas

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _repo_root() -> Path:
    if settings.SAAS_REPO_ROOT and settings.SAAS_REPO_ROOT.strip():
        return Path(settings.SAAS_REPO_ROOT.strip())
    # backend/app/services → parents[3] = repo root
    return Path(__file__).resolve().parents[3]


def _alocar_api_port(db: Session) -> int:
    start = max(1024, int(settings.SAAS_PROVISION_API_PORT_START or 8001))
    usados = {
        p
        for (p,) in db.query(ClienteSaaS.api_port).filter(ClienteSaaS.api_port.isnot(None)).all()
    }
    port = start
    while port in usados and port < 65535:
        port += 1
    if port > 65535:
        raise SaasErro("Não há portas API disponíveis para provisionamento")
    return port


def _montar_instancia_url(slug: str) -> str | None:
    base = (settings.SAAS_PROVISION_BASE_DOMAIN or "").strip().lstrip(".")
    if not base:
        return None
    return f"https://{slug}.{base}"


def enfileirar_provisionamento(db: Session, cliente_id: int) -> ClienteSaaS:
    row = obter(db, cliente_id)
    if row.provisionamento_status == "em_progresso":
        raise SaasErro("Provisionamento já em andamento para este cliente")
    if row.provisionamento_status == "sucesso" and row.instancia_url:
        raise SaasErro("Instância já provisionada; use registrar-instância para corrigir a URL")

    if row.api_port is None:
        row.api_port = _alocar_api_port(db)

    row.provisionamento_solicitado = True
    row.provisionamento_status = "pendente"
    row.provisionamento_mensagem = "Aguardando worker de provisionamento"
    row.provisionamento_atualizado_em = _utcnow()
    db.flush()

    notificar_equipe_saas(
        db,
        subject=f"[DeskRudder] Provisionamento solicitado — {row.nome} ({row.slug})",
        body=(
            f"Cliente: {row.nome}\n"
            f"Slug: {row.slug}\n"
            f"Porta API: {row.api_port}\n"
            f"Status: pendente\n"
            f"Execução automática: {'sim' if settings.SAAS_PROVISION_EXEC_ENABLED else 'não (fila manual)'}\n"
        ),
    )
    return row


def _executar_scripts(row: ClienteSaaS) -> str:
    root = _repo_root()
    provision = root / "deploy" / "scripts" / "provision-client.sh"
    stack = root / "deploy" / "scripts" / "stack-client.sh"
    if not provision.is_file() or not stack.is_file():
        raise RuntimeError(f"Scripts de deploy não encontrados em {root}/deploy/scripts")

    base = (settings.SAAS_PROVISION_BASE_DOMAIN or "").strip()
    if not base:
        raise RuntimeError("SAAS_PROVISION_BASE_DOMAIN não configurado")
    if row.api_port is None:
        raise RuntimeError("api_port não definido no cliente")

    dest = root / "deploy" / "clients" / row.slug
    if not dest.exists():
        cmd = [
            "bash",
            str(provision),
            "--slug",
            row.slug,
            "--base-domain",
            base,
            "--api-port",
            str(row.api_port),
        ]
        logger.info("SaaS provision: %s", " ".join(cmd))
        r = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            raise RuntimeError((r.stderr or r.stdout or "falha no provision-client.sh")[:2000])

    for step in ("migrate", "up", "health"):
        cmd = ["bash", str(stack), row.slug, step]
        logger.info("SaaS stack: %s", " ".join(cmd))
        r = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, timeout=1800)
        if r.returncode != 0:
            raise RuntimeError(
                f"Falha em stack-client.sh {step}: {(r.stderr or r.stdout or '')[:2000]}"
            )

    url = _montar_instancia_url(row.slug) or f"https://{row.slug}.{base}"
    return url


def processar_provisionamentos_pendentes(db: Session, *, limit: int = 5) -> int:
    """Worker: processa fila de provisionamento. Retorna quantos jobs tentou."""
    if not settings.SAAS_CONTROL_PLANE:
        return 0

    rows = (
        db.query(ClienteSaaS)
        .filter(ClienteSaaS.provisionamento_status == "pendente")
        .order_by(ClienteSaaS.id.asc())
        .limit(limit)
        .all()
    )
    if not rows:
        return 0

    processados = 0
    for row in rows:
        processados += 1
        row.provisionamento_status = "em_progresso"
        row.provisionamento_mensagem = "Provisionamento em andamento"
        row.provisionamento_atualizado_em = _utcnow()
        db.flush()

        if not settings.SAAS_PROVISION_EXEC_ENABLED:
            row.provisionamento_status = "aguardando_ops"
            row.provisionamento_mensagem = (
                "Fila registada. Execução automática desligada "
                "(SAAS_PROVISION_EXEC_ENABLED=false) — ops deve correr provision-client.sh / stack-client.sh."
            )
            row.provisionamento_atualizado_em = _utcnow()
            url = _montar_instancia_url(row.slug)
            if url and not row.instancia_url:
                row.instancia_url = url
            db.flush()
            continue

        try:
            url = _executar_scripts(row)
            row.instancia_url = url
            row.provisionamento_status = "sucesso"
            row.provisionamento_mensagem = "Instância provisionada com sucesso"
            row.provisionamento_atualizado_em = _utcnow()
            if row.status == "trial":
                # Mantém trial; ops ativa depois
                pass
            db.flush()
            notificar_equipe_saas(
                db,
                subject=f"[DeskRudder] Provisionamento OK — {row.slug}",
                body=f"URL: {url}\nSlug: {row.slug}\nPorta: {row.api_port}\n",
            )
        except Exception as e:
            logger.exception("Falha no provisionamento SaaS id=%s", row.id)
            row.provisionamento_status = "falha"
            row.provisionamento_mensagem = str(e)[:2000]
            row.provisionamento_atualizado_em = _utcnow()
            db.flush()
            notificar_equipe_saas(
                db,
                subject=f"[DeskRudder] Provisionamento FALHOU — {row.slug}",
                body=f"Erro: {row.provisionamento_mensagem}\n",
            )

    return processados


def contagem_fila(db: Session) -> dict[str, int]:
    q = (
        db.query(ClienteSaaS.provisionamento_status, func.count())
        .filter(ClienteSaaS.provisionamento_status.isnot(None))
        .group_by(ClienteSaaS.provisionamento_status)
        .all()
    )
    return {status: int(n) for status, n in q if status}
