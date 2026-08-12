"""Ciclo de vida da stack Docker do cliente (suspender / reativar) no control-plane."""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.models.cliente_saas import ClienteSaaS
from app.services.saas_clientes import SaasErro, obter
from app.services.saas_notify import notificar_equipe_saas

logger = logging.getLogger(__name__)

STACK_OPS_PENDENTE = ("down", "up")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _repo_root() -> Path:
    if settings.SAAS_REPO_ROOT and settings.SAAS_REPO_ROOT.strip():
        return Path(settings.SAAS_REPO_ROOT.strip())
    return Path(__file__).resolve().parents[3]


def _run_stack(slug: str, comando: str) -> None:
    root = _repo_root()
    stack = root / "deploy" / "scripts" / "stack-client.sh"
    if not stack.is_file():
        raise RuntimeError(f"Script não encontrado: {stack}")
    cmd = ["bash", str(stack), comando, slug]
    logger.info("SaaS stack lifecycle: %s", " ".join(cmd))
    r = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        raise RuntimeError(
            f"Falha em stack-client.sh {comando}: {(r.stderr or r.stdout or '')[:2000]}"
        )


def montar_comandos_stack(row: ClienteSaaS) -> str | None:
    pend = getattr(row, "stack_ops_pendente", None)
    if pend not in STACK_OPS_PENDENTE:
        return None
    slug = row.slug
    if pend == "down":
        return (
            f"# Parar stack do cliente (suspensão)\n"
            f"./deploy/scripts/stack-client.sh down {slug}\n"
            f"# Depois confirme no painel SaaS\n"
        )
    return (
        f"# Subir stack do cliente (reativação)\n"
        f"./deploy/scripts/stack-client.sh up {slug}\n"
        f"./deploy/scripts/stack-client.sh health {slug}\n"
        f"# Depois confirme no painel SaaS\n"
    )


def _tem_stack_provisionada(row: ClienteSaaS) -> bool:
    return row.provisionamento_status == "sucesso" or bool(
        (row.instancia_url or "").strip() and row.api_port is not None
    )


def aplicar_suspensao_stack(db: Session, row: ClienteSaaS) -> ClienteSaaS:
    """Após status=suspenso: para a stack (auto) ou pede down a ops."""
    if not _tem_stack_provisionada(row):
        row.stack_ops_pendente = None
        row.stack_ops_mensagem = None
        db.flush()
        return row

    if settings.SAAS_PROVISION_EXEC_ENABLED:
        try:
            _run_stack(row.slug, "down")
            row.stack_status = "stopped"
            row.stack_ops_pendente = None
            row.stack_ops_mensagem = "Stack parado automaticamente (stack-client.sh down)"
            row.stack_ops_atualizado_em = _utcnow()
        except Exception as e:
            logger.exception("Falha ao parar stack id=%s", row.id)
            row.stack_ops_pendente = "down"
            row.stack_ops_mensagem = str(e)[:2000]
            row.stack_status = "unknown"
            row.stack_ops_atualizado_em = _utcnow()
    else:
        row.stack_ops_pendente = "down"
        row.stack_ops_mensagem = (
            "Suspensão registada. Execução automática desligada — "
            "corra stack-client.sh down e confirme no painel."
        )
        row.stack_ops_atualizado_em = _utcnow()

    notificar_equipe_saas(
        db,
        subject=f"[DeskRudder] Cliente suspenso — {row.slug}",
        body=(
            f"Cliente: {row.nome}\n"
            f"Slug: {row.slug}\n"
            f"Stack: {row.stack_ops_mensagem or '—'}\n"
        ),
    )
    db.flush()
    return row


def aplicar_reativacao_stack(db: Session, row: ClienteSaaS) -> ClienteSaaS:
    """Após status=ativo: sobe a stack (auto) ou pede up a ops."""
    if not _tem_stack_provisionada(row):
        row.stack_ops_pendente = None
        row.stack_ops_mensagem = None
        db.flush()
        return row

    if settings.SAAS_PROVISION_EXEC_ENABLED:
        try:
            _run_stack(row.slug, "up")
            try:
                _run_stack(row.slug, "health")
            except Exception as he:
                logger.warning("Health após up falhou id=%s: %s", row.id, he)
            row.stack_status = "running"
            row.stack_ops_pendente = None
            row.stack_ops_mensagem = "Stack subida automaticamente (stack-client.sh up)"
            row.stack_ops_atualizado_em = _utcnow()
        except Exception as e:
            logger.exception("Falha ao subir stack id=%s", row.id)
            row.stack_ops_pendente = "up"
            row.stack_ops_mensagem = str(e)[:2000]
            row.stack_status = "unknown"
            row.stack_ops_atualizado_em = _utcnow()
    else:
        row.stack_ops_pendente = "up"
        row.stack_ops_mensagem = (
            "Reativação registada. Execução automática desligada — "
            "corra stack-client.sh up|health e confirme no painel."
        )
        row.stack_ops_atualizado_em = _utcnow()

    notificar_equipe_saas(
        db,
        subject=f"[DeskRudder] Cliente reativado — {row.slug}",
        body=(
            f"Cliente: {row.nome}\n"
            f"Slug: {row.slug}\n"
            f"Stack: {row.stack_ops_mensagem or '—'}\n"
        ),
    )
    db.flush()
    return row


def confirmar_stack_ops(db: Session, cliente_id: int) -> ClienteSaaS:
    """Ops confirma que down/up manual foi feito."""
    row = obter(db, cliente_id)
    pend = getattr(row, "stack_ops_pendente", None)
    if pend not in STACK_OPS_PENDENTE:
        raise SaasErro("Não há operação de stack pendente para confirmar")

    if pend == "down":
        row.stack_status = "stopped"
        row.stack_ops_mensagem = "Paragem da stack confirmada pela equipa ops"
    else:
        row.stack_status = "running"
        row.stack_ops_mensagem = "Subida da stack confirmada pela equipa ops"

    row.stack_ops_pendente = None
    row.stack_ops_atualizado_em = _utcnow()
    db.flush()
    return row
