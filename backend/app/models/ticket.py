from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    protocolo = Column(String(32), unique=True, nullable=False, index=True)  # #TYYYYMM-NNNN (legado: numérico)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)
    rede_id = Column(Integer, ForeignKey("redes.id"), nullable=True, index=True)
    setor_id = Column(Integer, ForeignKey("setores.id"), nullable=False)
    status_id = Column(Integer, ForeignKey("status_ticket.id"), nullable=False)
    atendente_id = Column(Integer, ForeignKey("atendentes.id"), nullable=True)  # responsável
    aberto_por_id = Column(Integer, ForeignKey("funcionarios_rede.id"), nullable=True)  # quem abriu (portal futuro)
    parent_ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True)
    assunto = Column(String(500), nullable=False)
    descricao = Column(Text, nullable=True)
    fechado_em = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    empresa = relationship("Empresa", back_populates="tickets")
    rede = relationship("Rede", back_populates="tickets")
    setor = relationship("Setor", back_populates="tickets")
    status = relationship("StatusTicket", back_populates="tickets")
    atendente = relationship("Atendente", back_populates="tickets_atendidos")
    aberto_por = relationship("FuncionarioRede", back_populates="tickets_abertos")
    parent = relationship(
        "Ticket",
        remote_side=[id],
        foreign_keys=[parent_ticket_id],
        back_populates="children",
    )
    children = relationship(
        "Ticket",
        foreign_keys=[parent_ticket_id],
        back_populates="parent",
    )
    vinculos_saida = relationship(
        "TicketVinculo",
        foreign_keys="TicketVinculo.ticket_id",
        back_populates="ticket",
    )
    vinculos_entrada = relationship(
        "TicketVinculo",
        foreign_keys="TicketVinculo.related_ticket_id",
        back_populates="related_ticket",
    )
    historicos = relationship("TicketHistorico", back_populates="ticket", order_by="TicketHistorico.created_at")
    mensagens = relationship(
        "TicketMensagem",
        back_populates="ticket",
        order_by="TicketMensagem.created_at",
    )


class TicketMensagem(Base):
    """Linha do tempo do ticket: abertura, mensagens da equipe (público ao suporte) e comentários internos."""

    __tablename__ = "ticket_mensagens"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    # abertura = texto inicial; publico = atualização visível à equipe; interno = só atendentes
    tipo = Column(String(20), nullable=False)
    corpo = Column(Text, nullable=False)
    autor_externo = Column(String(512), nullable=True)
    # Fila de e-mail ao cliente (#140): só preenchido quando notificar_cliente_por_email na criação.
    email_status = Column(String(32), nullable=True, index=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True, index=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    edit_lock_token = Column(String(64), nullable=True)
    edit_lock_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("Ticket", back_populates="mensagens")
    atendente = relationship("Atendente", back_populates="ticket_mensagens")


class TicketHistorico(Base):
    """Auditoria: quem alterou o quê e quando."""

    __tablename__ = "ticket_historico"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    atendente_id = Column(Integer, ForeignKey("atendentes.id"), nullable=True)  # quem fez a alteração
    campo = Column(String(50), nullable=False)  # ex: status_id, atendente_id, descricao
    valor_antigo = Column(Text, nullable=True)
    valor_novo = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("Ticket", back_populates="historicos")
    atendente = relationship("Atendente", back_populates="historicos")
