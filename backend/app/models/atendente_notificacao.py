from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class AtendenteNotificacaoPreferencias(Base):
    __tablename__ = "atendente_notificacao_preferencias"

    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="CASCADE"), primary_key=True)
    email_habilitado = Column(Boolean, nullable=False, default=True)
    email_ticket_atribuido = Column(Boolean, nullable=False, default=True)
    email_nova_mensagem = Column(Boolean, nullable=False, default=True)
    email_sla_em_risco = Column(Boolean, nullable=False, default=True)
    email_sla_violado = Column(Boolean, nullable=False, default=True)
    push_habilitado = Column(Boolean, nullable=False, default=False)
    push_fila = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    atendente = relationship("Atendente", backref="notificacao_preferencias", uselist=False)


class NotificacaoEmailOutbox(Base):
    __tablename__ = "notificacao_email_outbox"

    id = Column(Integer, primary_key=True, index=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="CASCADE"), nullable=False, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=True, index=True)
    tipo = Column(String(40), nullable=False)
    dedup_key = Column(String(120), nullable=False, unique=True, index=True)
    to_email = Column(String(255), nullable=False)
    subject = Column(String(998), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pendente", index=True)
    tentativas = Column(Integer, nullable=False, default=0)
    scheduled_at = Column(DateTime(timezone=True), nullable=False, index=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    atendente = relationship("Atendente", backref="notificacoes_email_outbox")
    ticket = relationship("Ticket", backref="notificacoes_email_outbox")
