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
    return f"https://{slug}.{base}/"


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


def _escrever_modulos_no_client_env(root, row: ClienteSaaS) -> None:
    """Grava SAAS_MODULOS no client.env a partir do snapshot / plano da licença."""
    mods = list(getattr(row, "modulos_snapshot", None) or [])
    if not mods:
        mods = ["helpdesk"]
    env_path = root / "deploy" / "clients" / row.slug / "client.env"
    if not env_path.is_file():
        return
    line = f"SAAS_MODULOS={','.join(mods)}"
    text = env_path.read_text(encoding="utf-8")
    if "SAAS_MODULOS=" in text:
        lines = []
        for ln in text.splitlines():
            if ln.startswith("SAAS_MODULOS="):
                lines.append(line)
            else:
                lines.append(ln)
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        env_path.write_text(text.rstrip() + f"\n\n# Módulos do plano comercial\n{line}\n", encoding="utf-8")
    logger.info("SAAS_MODULOS escrito em %s: %s", env_path, line)


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

    _escrever_modulos_no_client_env(root, row)

    for step in ("migrate", "up", "seed", "health"):
        # stack-client.sh <comando> <slug>
        cmd = ["bash", str(stack), step, row.slug]
        logger.info("SaaS stack: %s", " ".join(cmd))
        r = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, timeout=1800)
        # seed pode falhar se já existir admin — não bloqueia health
        if r.returncode != 0 and step != "seed":
            raise RuntimeError(
                f"Falha em stack-client.sh {step}: {(r.stderr or r.stdout or '')[:2000]}"
            )

    url = _montar_instancia_url(row.slug) or f"https://{row.slug}.{base}/"
    return url


def montar_comandos_ops(row: ClienteSaaS) -> str | None:
    """Bloco shell para ops correr no host (caminho SAAS_PROVISION_EXEC_ENABLED=false)."""
    if row.provisionamento_status not in ("pendente", "em_progresso", "aguardando_ops", "falha"):
        return None
    base = (settings.SAAS_PROVISION_BASE_DOMAIN or "").strip().lstrip(".") or "deskrudder.com.br"
    port = row.api_port
    port_txt = str(port) if port is not None else "<api_port>"
    slug = row.slug
    return (
        f"# Na raiz do repositório no host de deploy\n"
        f"./deploy/scripts/provision-client.sh --slug {slug} --base-domain {base} --api-port {port_txt}\n"
        f"./deploy/scripts/stack-client.sh migrate {slug}\n"
        f"./deploy/scripts/stack-client.sh up {slug}\n"
        f"./deploy/scripts/stack-client.sh health {slug}\n"
        f"# Após provision, confirme SAAS_MODULOS no client.env (módulos do plano)\n"
        f"# Se health OK, confirme no painel SaaS (ou: curl -sf http://127.0.0.1:{port_txt}/health)\n"
    )


def confirmar_provisionamento(
    db: Session,
    cliente_id: int,
    *,
    instancia_url: str | None = None,
) -> ClienteSaaS:
    """Ops confirma que a instância subiu (health ok) após scripts manuais."""
    row = obter(db, cliente_id)
    if row.provisionamento_status not in ("aguardando_ops", "falha"):
        raise SaasErro(
            "Só é possível confirmar provisionamento em status aguardando_ops ou falha",
            400,
        )
    url = (instancia_url or "").strip() or None
    if not url:
        url = row.instancia_url or _montar_instancia_url(row.slug)
    if not url:
        raise SaasErro("Informe a URL da instância ou configure SAAS_PROVISION_BASE_DOMAIN")
    if "://" not in url:
        url = f"https://{url}"

    row.instancia_url = url
    row.provisionamento_solicitado = True
    row.provisionamento_status = "sucesso"
    row.provisionamento_mensagem = "Provisionamento confirmado pela equipa ops (health ok)"
    row.provisionamento_atualizado_em = _utcnow()
    row.stack_status = "running"
    row.stack_ops_pendente = None
    row.stack_ops_mensagem = "Stack em execução após confirmação de provisionamento"
    row.stack_ops_atualizado_em = _utcnow()
    db.flush()

    from app.services.saas_notify import notificar_contacto_entrega

    notificar_contacto_entrega(db, row)
    return row


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
            row.stack_status = "running"
            row.stack_ops_pendente = None
            row.stack_ops_mensagem = "Stack em execução após provisionamento automático"
            row.stack_ops_atualizado_em = _utcnow()
            if row.status == "trial":
                # Mantém trial; ops ativa depois
                pass
            db.flush()
            from app.services.saas_notify import notificar_contacto_entrega

            notificar_contacto_entrega(db, row)
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
