from sqlalchemy import Column, Integer, String, Boolean, DateTime, Table, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

# Tabela associativa: atendente <-> setor (N:N)
atendente_setor = Table(
    "atendente_setor",
    Base.metadata,
    Column("atendente_id", Integer, ForeignKey("atendentes.id", ondelete="CASCADE"), primary_key=True),
    Column("setor_id", Integer, ForeignKey("setores.id", ondelete="CASCADE"), primary_key=True),
)


class Atendente(Base):
    """Usuário interno: admin, atendente ou comercial."""

    __tablename__ = "atendentes"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_atendentes_tenant_email"),)

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    senha_hash = Column(String(255), nullable=False)
    nome = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="atendente")  # admin | atendente | comercial
    ativo = Column(Boolean, default=True)
    must_change_password = Column(Boolean, nullable=False, default=False)
    # Presença online (#546+): heartbeat gravado no DB (funciona com Gunicorn N>1).
    presenca_online_desde = Column(DateTime(timezone=True), nullable=True)
    presenca_heartbeat_em = Column(DateTime(timezone=True), nullable=True, index=True)
    # Incrementado ao forçar saída — invalida access/refresh tokens com claim "ver" antigo.
    token_version = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    setores = relationship(
        "Setor",
        secondary=atendente_setor,
        back_populates="atendentes",
    )
    tickets_atendidos = relationship("Ticket", back_populates="atendente")
    historicos = relationship("TicketHistorico", back_populates="atendente")
    ticket_mensagens = relationship("TicketMensagem", back_populates="atendente")


# Alias para uso nos models (Setor usa "atendente_setor" como secondary string)
AtendenteSetor = atendente_setor
