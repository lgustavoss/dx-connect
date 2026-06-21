"""Drill-down cross-filter dos dashboards analíticos."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import exists, select

from app.models import Ticket
from app.models.ticket_avaliacao import TicketAvaliacao
from app.models.whatsapp_chat import WhatsappChat, WhatsappMensagem

TICKET_DRILL_TIPOS = frozenset(
    {"atendente", "empresa", "rede", "motivo", "status", "prioridade", "canal", "nota"}
)
CHAT_DRILL_TIPOS = frozenset({"atendente", "estado", "encerramento", "nota"})


@dataclass(frozen=True)
class TicketDrillDown:
    tipo: str | None = None
    valor: str | None = None

    @classmethod
    def parse(
        cls,
        *,
        drill_tipo: str | None = None,
        drill_valor: str | None = None,
        atendente_filtro_id: int | None = None,
    ) -> TicketDrillDown:
        if drill_tipo and drill_valor:
            tipo = drill_tipo.strip().lower()
            if tipo in TICKET_DRILL_TIPOS:
                return cls(tipo=tipo, valor=drill_valor.strip())
        if atendente_filtro_id is not None:
            return cls(tipo="atendente", valor=str(atendente_filtro_id))
        return cls()

    def without(self, dimension: str) -> TicketDrillDown:
        if self.tipo == dimension:
            return TicketDrillDown()
        return self

    @property
    def ativo(self) -> bool:
        return bool(self.tipo and self.valor)


@dataclass(frozen=True)
class ChatDrillDown:
    tipo: str | None = None
    valor: str | None = None

    @classmethod
    def parse(
        cls,
        *,
        drill_tipo: str | None = None,
        drill_valor: str | None = None,
        atendente_filtro_id: int | None = None,
    ) -> ChatDrillDown:
        if drill_tipo and drill_valor:
            tipo = drill_tipo.strip().lower()
            if tipo in CHAT_DRILL_TIPOS:
                return cls(tipo=tipo, valor=drill_valor.strip())
        if atendente_filtro_id is not None:
            return cls(tipo="atendente", valor=str(atendente_filtro_id))
        return cls()

    def without(self, dimension: str) -> ChatDrillDown:
        if self.tipo == dimension:
            return ChatDrillDown()
        return self

    @property
    def ativo(self) -> bool:
        return bool(self.tipo and self.valor)


def apply_ticket_drill_down(stmt, drill: TicketDrillDown, *, canal_expr=None):
    if not drill.ativo:
        return stmt
    tipo, valor = drill.tipo, drill.valor
    assert tipo is not None and valor is not None

    if tipo == "atendente":
        return stmt.where(Ticket.atendente_id == int(valor))
    if tipo == "empresa":
        eid = int(valor)
        if eid == 0:
            return stmt.where(Ticket.empresa_id.is_(None))
        return stmt.where(Ticket.empresa_id == eid)
    if tipo == "rede":
        rid = int(valor)
        if rid == 0:
            return stmt.where(Ticket.rede_id.is_(None))
        return stmt.where(Ticket.rede_id == rid)
    if tipo == "motivo":
        mid = int(valor)
        if mid == 0:
            return stmt.where(Ticket.motivo_id.is_(None))
        return stmt.where(Ticket.motivo_id == mid)
    if tipo == "status":
        return stmt.where(Ticket.status_id == int(valor))
    if tipo == "prioridade":
        return stmt.where(Ticket.prioridade == valor)
    if tipo == "canal":
        if canal_expr is None:
            raise ValueError("canal_expr obrigatório para drill de canal")
        return stmt.where(canal_expr == valor)
    if tipo == "nota":
        nota = int(valor)
        avaliacao = (
            select(TicketAvaliacao.id)
            .where(
                TicketAvaliacao.ticket_id == Ticket.id,
                TicketAvaliacao.nota == nota,
            )
            .correlate(Ticket)
            .exists()
        )
        return stmt.where(avaliacao)
    return stmt


def apply_chat_drill_down(stmt, drill: ChatDrillDown):
    if not drill.ativo:
        return stmt
    tipo, valor = drill.tipo, drill.valor
    assert tipo is not None and valor is not None

    if tipo == "atendente":
        return stmt.where(WhatsappChat.atendente_id == int(valor))
    if tipo == "estado":
        return stmt.where(WhatsappChat.estado == valor)
    if tipo == "nota":
        return stmt.where(WhatsappChat.avaliacao_nota == int(valor))
    if tipo == "encerramento":
        encerrados = WhatsappChat.encerramento_at.isnot(None)
        if valor == "manual":
            inatividade = (
                select(WhatsappMensagem.id)
                .where(
                    WhatsappMensagem.chat_id == WhatsappChat.id,
                    WhatsappMensagem.evento_sistema == "auto_encerrado_inatividade",
                )
                .correlate(WhatsappChat)
                .exists()
            )
            return stmt.where(encerrados, ~inatividade)
        if valor == "inatividade":
            inatividade = (
                select(WhatsappMensagem.id)
                .where(
                    WhatsappMensagem.chat_id == WhatsappChat.id,
                    WhatsappMensagem.evento_sistema == "auto_encerrado_inatividade",
                )
                .correlate(WhatsappChat)
                .exists()
            )
            return stmt.where(encerrados, inatividade)
    return stmt
