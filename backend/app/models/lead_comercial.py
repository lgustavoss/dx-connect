"""Leads comerciais B2B da landing (DR-06 / #516) — separado do portal /kb."""

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base

STATUS_LEAD_COMERCIAL = ("novo", "em_atendimento", "fechado")


class LeadComercial(Base):
    __tablename__ = "leads_comerciais"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(200), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    empresa = Column(String(200), nullable=True)
    mensagem = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="novo", index=True)
    origem = Column(String(80), nullable=False, default="landing")
    notas_internas = Column(Text, nullable=True)
    cliente_saas_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
