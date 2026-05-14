"""Contador mensal atómico para protocolos de tickets (#T…) e chats (#C…)."""

from sqlalchemy import Column, Integer, String

from app.database import Base


class ProtocolSequence(Base):
    __tablename__ = "protocol_sequences"

    kind = Column(String(1), primary_key=True)  # "T" | "C"
    ano_mes = Column(String(6), primary_key=True)  # YYYYMM (America/Sao_Paulo)
    last_value = Column(Integer, nullable=False, default=0)
