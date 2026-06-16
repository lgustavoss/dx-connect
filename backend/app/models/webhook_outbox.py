from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class WebhookOutbox(Base):
    """Fila de POSTs HTTP para integrações externas (#119)."""

    __tablename__ = "webhook_outbox"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    dedup_key = Column(String(255), nullable=False, index=True)
    target_url = Column(String(2048), nullable=False)
    payload_json = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="pendente", index=True)
    tentativas = Column(Integer, nullable=False, default=0, server_default="0")
    last_error = Column(Text, nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=False, index=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
