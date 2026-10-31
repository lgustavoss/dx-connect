from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Dispositivo(Base):
    """Token FCM do aparelho do atendente (#1315)."""

    __tablename__ = "dispositivos"
    __table_args__ = (UniqueConstraint("token", name="uq_dispositivos_token"),)

    id = Column(Integer, primary_key=True, index=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(512), nullable=False)
    plataforma = Column(String(32), nullable=False, default="android")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    atendente = relationship("Atendente", backref="dispositivos")


class FcmOutbox(Base):
    """Fila de envio FCM — worker após commit (#1315)."""

    __tablename__ = "fcm_outbox"

    id = Column(Integer, primary_key=True, index=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    dedup_key = Column(String(255), nullable=False, unique=True, index=True)
    payload_json = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="pendente", index=True)
    tentativas = Column(Integer, nullable=False, default=0, server_default="0")
    last_error = Column(Text, nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=False, index=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    atendente = relationship("Atendente", backref="fcm_outbox")
