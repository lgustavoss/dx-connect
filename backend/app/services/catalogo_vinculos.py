"""Recusa desativar item de catálogo que ainda aparece em outro cadastro."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.crm import CrmLead, CrmNegociacao
from app.models.empresa import Empresa
from app.models.portal_chat import PortalChat
from app.models.portal_chat_demanda import PortalChatDemanda
from app.models.ticket import Ticket
from app.models.ticket_classificacao import TicketMotivo
from app.models.whatsapp_chat import WhatsappChat
from app.models.whatsapp_chat_demanda import WhatsappChatDemanda


def recusar_desativar_em_uso(n: int, *, um: str, varios: str) -> None:
    if n <= 0:
        return
    raise ValueError(um if n == 1 else varios.format(n=n))


def _quantidade(n: int, singular: str, plural: str) -> str | None:
    if n <= 0:
        return None
    return f"1 {singular}" if n == 1 else f"{n} {plural}"


def _juntar_e(*partes: str | None) -> str | None:
    itens = [p for p in partes if p]
    if not itens:
        return None
    if len(itens) == 1:
        return itens[0]
    return f"{', '.join(itens[:-1])} e {itens[-1]}"


def garantir_tipo_negocio_pode_desativar(db: Session, tipo_id: int) -> None:
    n = (
        db.query(func.count(Empresa.id))
        .filter(Empresa.tipo_negocio_id == tipo_id, Empresa.ativo.is_(True))
        .scalar()
        or 0
    )
    recusar_desativar_em_uso(
        n,
        um="Não é possível desativar este tipo de negócio: 1 empresa ativa ainda o usa.",
        varios="Não é possível desativar este tipo de negócio: {n} empresas ativas ainda o usam.",
    )


def _contar_tickets_abertos_motivo(db: Session, motivo_id: int) -> int:
    return int(
        db.query(func.count(Ticket.id))
        .filter(Ticket.motivo_id == motivo_id, Ticket.fechado_em.is_(None))
        .scalar()
        or 0
    )


def _contar_tickets_abertos_natureza(db: Session, natureza_id: int) -> int:
    return int(
        db.query(func.count(Ticket.id))
        .join(TicketMotivo, Ticket.motivo_id == TicketMotivo.id)
        .filter(TicketMotivo.natureza_id == natureza_id, Ticket.fechado_em.is_(None))
        .scalar()
        or 0
    )


def _contar_chats_abertos(db: Session, *, motivo_id: int | None = None, natureza_id: int | None = None) -> int:
    wa_q = (
        db.query(func.count(func.distinct(WhatsappChat.id)))
        .join(WhatsappChatDemanda, WhatsappChatDemanda.chat_id == WhatsappChat.id)
        .filter(WhatsappChat.estado != "encerrado")
    )
    portal_q = (
        db.query(func.count(func.distinct(PortalChat.id)))
        .join(PortalChatDemanda, PortalChatDemanda.chat_id == PortalChat.id)
        .filter(PortalChat.estado != "encerrado")
    )
    if motivo_id is not None:
        wa_q = wa_q.filter(WhatsappChatDemanda.motivo_id == motivo_id)
        portal_q = portal_q.filter(PortalChatDemanda.motivo_id == motivo_id)
    if natureza_id is not None:
        wa_q = wa_q.filter(WhatsappChatDemanda.natureza_id == natureza_id)
        portal_q = portal_q.filter(PortalChatDemanda.natureza_id == natureza_id)
    return int(wa_q.scalar() or 0) + int(portal_q.scalar() or 0)


def _recusar_classificacao_em_aberto(
    *,
    prefixo: str,
    objeto: str,
    n_tickets: int,
    n_chats: int,
    n_motivos: int = 0,
) -> None:
    texto = _juntar_e(
        _quantidade(n_motivos, "motivo", "motivos"),
        _quantidade(n_tickets, "ticket em aberto", "tickets em aberto"),
        _quantidade(n_chats, "chat em aberto", "chats em aberto"),
    )
    if not texto:
        return
    verbo = "usa" if (n_motivos + n_tickets + n_chats) == 1 else "usam"
    raise ValueError(f"{prefixo} {texto} ainda {objeto} {verbo}.")


def garantir_motivo_pode_desativar(db: Session, motivo_id: int) -> None:
    _recusar_classificacao_em_aberto(
        prefixo="Não é possível desativar este motivo:",
        objeto="o",
        n_tickets=_contar_tickets_abertos_motivo(db, motivo_id),
        n_chats=_contar_chats_abertos(db, motivo_id=motivo_id),
    )


def garantir_natureza_pode_desativar(db: Session, natureza_id: int) -> None:
    n_motivos = int(
        db.query(func.count(TicketMotivo.id))
        .filter(TicketMotivo.natureza_id == natureza_id, TicketMotivo.ativo.is_(True))
        .scalar()
        or 0
    )
    _recusar_classificacao_em_aberto(
        prefixo="Não é possível desativar esta natureza:",
        objeto="a",
        n_motivos=n_motivos,
        n_tickets=_contar_tickets_abertos_natureza(db, natureza_id),
        n_chats=_contar_chats_abertos(db, natureza_id=natureza_id),
    )


def garantir_estagio_funil_pode_desativar(db: Session, estagio_id: int) -> None:
    n_leads = int(
        db.query(func.count(CrmLead.id))
        .filter(
            CrmLead.estagio_id == estagio_id,
            CrmLead.ativo.is_(True),
            CrmLead.perdido_em.is_(None),
        )
        .scalar()
        or 0
    )
    n_negs = int(
        db.query(func.count(CrmNegociacao.id))
        .filter(CrmNegociacao.estagio_id == estagio_id, CrmNegociacao.ativa.is_(True))
        .scalar()
        or 0
    )
    texto = _juntar_e(
        _quantidade(n_leads, "lead", "leads"),
        _quantidade(n_negs, "negociação", "negociações"),
    )
    if not texto:
        return
    verbo = "está" if (n_leads + n_negs) == 1 else "estão"
    raise ValueError(f"Não é possível desativar este estágio: {texto} ainda {verbo} nele.")
