"""Decisões admin sobre sugestões de motivo a partir de «Outros» (#594)."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

STATUS_ACEITA = "aceita"
STATUS_IGNORADA = "ignorada"
STATUS_SUGESTAO = frozenset({STATUS_ACEITA, STATUS_IGNORADA})


class WhatsappDemandaMotivoSugestao(Base):
    __tablename__ = "whatsapp_demanda_motivo_sugestoes"
    __table_args__ = (
        UniqueConstraint(
            "natureza_id",
            "texto_normalizado",
            name="uq_wpp_demanda_motivo_sugestao_nat_texto",
        ),
    )

    id = Column(Integer, primary_key=True)
    natureza_id = Column(
        Integer, ForeignKey("ticket_naturezas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    texto_normalizado = Column(String(500), nullable=False)
    texto_exemplo = Column(String(500), nullable=False)
    status = Column(String(16), nullable=False, index=True)
    motivo_criado_id = Column(
        Integer, ForeignKey("ticket_motivos.id", ondelete="SET NULL"), nullable=True
    )
    decidido_por_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    decidido_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    natureza = relationship("TicketNatureza")
    motivo_criado = relationship("TicketMotivo")
    decidido_por = relationship("Atendente")
