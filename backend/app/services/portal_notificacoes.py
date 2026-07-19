"""E-mails ao funcionário sobre eventos do ticket no portal (#303)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models.funcionario_rede import FuncionarioRede
from app.models.ticket import Ticket, TicketMensagem
from app.services.email_send_sistema import enviar_mensagem_texto_sistema

logger = logging.getLogger(__name__)

# Debounce simples em memória por processo (idempotência básica)
_ultimos_envios: dict[str, datetime] = {}
_DEBOUNCE = timedelta(minutes=2)


def clear_debounce_for_tests() -> None:
    """Limpa cache de debounce (apenas testes)."""
    _ultimos_envios.clear()


def _public_app_origin() -> str:
    host = (settings.CLIENT_APP_HOST or "").strip()
    if host:
        host = host.removeprefix("https://").removeprefix("http://").split("/")[0]
        proto = "https" if settings.is_production else "http"
        return f"{proto}://{host}"
    if not settings.is_production:
        return "http://localhost:5173"
    base = (settings.CONNECT_APP_BASE_DOMAIN or "").strip()
    if base:
        return f"https://{base}"
    return "http://localhost:5173"


def _pode_enviar(chave: str) -> bool:
    agora = datetime.now(timezone.utc)
    ultimo = _ultimos_envios.get(chave)
    if ultimo and agora - ultimo < _DEBOUNCE:
        return False
    _ultimos_envios[chave] = agora
    # Limpa chaves antigas
    if len(_ultimos_envios) > 500:
        limite = agora - timedelta(hours=1)
        for k, v in list(_ultimos_envios.items()):
            if v < limite:
                _ultimos_envios.pop(k, None)
    return True


def build_portal_ticket_link(ticket_id: int) -> str:
    origin = _public_app_origin().rstrip("/")
    return f"{origin}/portal/tickets/{ticket_id}"


def _destinatario_portal(db: Session, ticket: Ticket) -> FuncionarioRede | None:
    if not ticket.aberto_por_id:
        return None
    f = db.query(FuncionarioRede).filter(FuncionarioRede.id == ticket.aberto_por_id).first()
    if not f or not f.ativo:
        return None
    if not (f.email or "").strip():
        return None
    if not getattr(f, "notificar_email_portal", True):
        return None
    if not (f.senha_hash or "").strip():
        # Sem acesso ao portal: ainda notifica se tiver e-mail (acompanhamento)
        pass
    return f


def notificar_funcionario_mensagem_publica(
    db: Session,
    *,
    ticket: Ticket,
    mensagem: TicketMensagem,
) -> None:
    """Dispara e-mail quando a equipe envia mensagem pública no ticket aberto pelo portal."""
    if mensagem.tipo != "publico":
        return
    if not mensagem.atendente_id:
        return
    dest = _destinatario_portal(db, ticket)
    if not dest:
        return
    chave = f"msg:{ticket.id}:{mensagem.id}"
    if not _pode_enviar(chave):
        return
    link = build_portal_ticket_link(ticket.id)
    nome = (dest.nome or "").strip() or "olá"
    subject = f"Nova resposta no chamado {ticket.protocolo}"
    trecho = (mensagem.corpo or "").strip()
    if len(trecho) > 280:
        trecho = trecho[:277] + "…"
    body = (
        f"Olá, {nome},\n\n"
        f"Há uma nova mensagem da equipe no chamado {ticket.protocolo}.\n\n"
        f"{trecho}\n\n"
        f"Acompanhe no portal:\n{link}\n\n"
        "— Equipe de suporte"
    )
    try:
        enviar_mensagem_texto_sistema(db, to_addr=str(dest.email), subject=subject, body=body)
    except ValueError as e:
        logger.warning("Portal e-mail: envio indisponível (%s)", e)
    except Exception:
        logger.exception("Portal e-mail: falha ticket_id=%s", ticket.id)


def notificar_funcionario_status(
    db: Session,
    *,
    ticket: Ticket,
    status_nome: str,
    status_slug: str | None = None,
) -> None:
    """Avisa mudança de status relevante (encerrado / aguardando cliente)."""
    slug = (status_slug or "").strip().lower()
    relevantes = {"fechado", "aguardando_cliente", "resolvido"}
    if slug and slug not in relevantes:
        return
    dest = _destinatario_portal(db, ticket)
    if not dest:
        return
    chave = f"st:{ticket.id}:{slug or status_nome}"
    if not _pode_enviar(chave):
        return
    link = build_portal_ticket_link(ticket.id)
    nome = (dest.nome or "").strip() or "olá"
    subject = f"Atualização do chamado {ticket.protocolo}: {status_nome}"
    body = (
        f"Olá, {nome},\n\n"
        f"O status do chamado {ticket.protocolo} foi atualizado para «{status_nome}».\n\n"
        f"Veja os detalhes:\n{link}\n\n"
        "— Equipe de suporte"
    )
    try:
        enviar_mensagem_texto_sistema(db, to_addr=str(dest.email), subject=subject, body=body)
    except ValueError as e:
        logger.warning("Portal e-mail status: envio indisponível (%s)", e)
    except Exception:
        logger.exception("Portal e-mail status: falha ticket_id=%s", ticket.id)
