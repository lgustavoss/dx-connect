from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PushSubscription(Base):
    """Subscription Web Push do atendente (por dispositivo / browser) (#693)."""

    __tablename__ = "push_subscription"
    __table_args__ = (UniqueConstraint("endpoint", name="uq_push_subscription_endpoint"),)

    id = Column(Integer, primary_key=True, index=True)
    atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="CASCADE"), nullable=False, index=True)
    endpoint = Column(String(2048), nullable=False)
    p256dh = Column(String(255), nullable=False)
    auth = Column(String(255), nullable=False)
    user_agent = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    atendente = relationship("Atendente", backref="push_subscriptions")


class PushOutbox(Base):
    """Fila de envio Web Push — worker após commit (#693)."""

    __tablename__ = "push_outbox"

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

    atendente = relationship("Atendente", backref="push_outbox")
