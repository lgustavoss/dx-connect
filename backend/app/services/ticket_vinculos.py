"""Criação e listagem de vínculos entre tickets (#115)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.atendente import Atendente
from app.models.empresa import Empresa
from app.models.status_ticket import StatusTicket
from app.models.ticket import Ticket, TicketMensagem
from app.models.ticket_vinculo import TIPO_DUPLICADO_DE, TIPO_RELACIONADO_A, TIPOS_VINCULO, TicketVinculo


def _protocolo_exibicao(protocolo: str) -> str:
    s = (protocolo or "").strip()
    if not s:
        return "—"
    if s.startswith("#"):
        return s
    if s.isdigit():
        return f"#{s}"
    return s


def normalizar_par_vinculo(*, ticket_id: int, related_ticket_id: int, tipo: str) -> tuple[int, int]:
    if tipo == TIPO_RELACIONADO_A:
        a, b = sorted((ticket_id, related_ticket_id))
        return a, b
    return ticket_id, related_ticket_id


def listar_vinculos(db: Session, ticket_id: int) -> list[TicketVinculo]:
    return (
        db.query(TicketVinculo)
        .options(
            joinedload(TicketVinculo.ticket).joinedload(Ticket.status),
            joinedload(TicketVinculo.related_ticket).joinedload(Ticket.status),
        )
        .filter(or_(TicketVinculo.ticket_id == ticket_id, TicketVinculo.related_ticket_id == ticket_id))
        .order_by(TicketVinculo.id.asc())
        .all()
    )


def vinculo_ja_existe(db: Session, *, ticket_id: int, related_ticket_id: int, tipo: str) -> bool:
    tid, rid = normalizar_par_vinculo(ticket_id=ticket_id, related_ticket_id=related_ticket_id, tipo=tipo)
    return (
        db.query(TicketVinculo.id)
        .filter(
            TicketVinculo.ticket_id == tid,
            TicketVinculo.related_ticket_id == rid,
            TicketVinculo.tipo == tipo,
        )
        .first()
        is not None
    )


def outro_ticket_id(v: TicketVinculo, perspectiva_ticket_id: int) -> int:
    if v.ticket_id == perspectiva_ticket_id:
        return v.related_ticket_id
    return v.ticket_id


def rotulo_vinculo(v: TicketVinculo, perspectiva_ticket_id: int) -> str:
    if v.tipo == TIPO_RELACIONADO_A:
        return "Relacionado a"
    if v.ticket_id == perspectiva_ticket_id:
        return "Duplicado de"
    return "É duplicado deste"


def _rede_id_do_ticket(db: Session, ticket: Ticket) -> int | None:
    if ticket.rede_id is not None:
        return ticket.rede_id
    if ticket.empresa_id is None:
        return None
    if ticket.empresa is not None and ticket.empresa.rede_id is not None:
        return ticket.empresa.rede_id
    return db.query(Empresa.rede_id).filter(Empresa.id == ticket.empresa_id).scalar()


def validar_duplicado_mesma_rede_empresa(db: Session, *, ticket: Ticket, related: Ticket) -> None:
    if ticket.empresa_id is None or related.empresa_id is None:
        raise ValueError("Para marcar como duplicado, ambos os tickets precisam ter empresa definida.")
    if ticket.empresa_id != related.empresa_id:
        raise ValueError("Tickets duplicados devem ser da mesma empresa.")
    rede_ticket = _rede_id_do_ticket(db, ticket)
    rede_related = _rede_id_do_ticket(db, related)
    if rede_ticket is None or rede_related is None:
        raise ValueError("Para marcar como duplicado, ambos os tickets precisam pertencer a uma rede.")
    if rede_ticket != rede_related:
        raise ValueError("Tickets duplicados devem ser da mesma rede.")


def criar_vinculo(
    db: Session,
    *,
    ticket: Ticket,
    related: Ticket,
    tipo: str,
    atendente: Atendente,
) -> TicketVinculo:
    if tipo not in TIPOS_VINCULO:
        raise ValueError(f"Tipo de vínculo inválido: {tipo}")
    if ticket.id == related.id:
        raise ValueError("Um ticket não pode ser vinculado a si mesmo.")
    if ticket.tenant_id != related.tenant_id:
        raise ValueError("Os tickets devem pertencer ao mesmo tenant.")
    if tipo == TIPO_DUPLICADO_DE:
        validar_duplicado_mesma_rede_empresa(db, ticket=ticket, related=related)
    if vinculo_ja_existe(db, ticket_id=ticket.id, related_ticket_id=related.id, tipo=tipo):
        raise ValueError("Este vínculo já existe.")

    tid, rid = normalizar_par_vinculo(ticket_id=ticket.id, related_ticket_id=related.id, tipo=tipo)
    row = TicketVinculo(
        tenant_id=ticket.tenant_id,
        ticket_id=tid,
        related_ticket_id=rid,
        tipo=tipo,
        created_by_id=atendente.id,
    )
    db.add(row)
    db.flush()
    return row


def remover_vinculo(db: Session, *, vinculo_id: int, ticket_id: int) -> None:
    row = (
        db.query(TicketVinculo)
        .filter(
            TicketVinculo.id == vinculo_id,
            or_(TicketVinculo.ticket_id == ticket_id, TicketVinculo.related_ticket_id == ticket_id),
        )
        .first()
    )
    if not row:
        raise ValueError("Vínculo não encontrado.")
    db.delete(row)


def fechar_ticket_como_duplicado(
    db: Session,
    *,
    duplicado: Ticket,
    original: Ticket,
    atendente: Atendente,
) -> bool:
    """Fecha o ticket duplicado e registra mensagem pública apontando para o original."""
    if duplicado.fechado_em is not None:
        return False

    status_fechado = (
        db.query(StatusTicket)
        .filter(func.lower(StatusTicket.slug) == "fechado", StatusTicket.ativo.is_(True))
        .first()
    )
    if status_fechado is None:
        raise ValueError('Cadastre um status ativo com slug "fechado" para encerrar tickets duplicados.')

    proto = _protocolo_exibicao(original.protocolo)
    corpo = (
        f"Este chamado foi identificado como duplicado de {proto}. "
        f"O atendimento continua no ticket original ({proto} — {original.assunto})."
    )
    db.add(
        TicketMensagem(
            ticket_id=duplicado.id,
            atendente_id=atendente.id,
            tipo="publico",
            corpo=corpo,
        )
    )
    duplicado.status_id = status_fechado.id
    duplicado.fechado_em = datetime.now(timezone.utc)
    return True
