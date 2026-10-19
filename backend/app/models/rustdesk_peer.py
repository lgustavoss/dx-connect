from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class RustdeskPeer(Base):
    """Cache dos computadores registrados no hbbs. O vínculo com o PDV é o ID remoto, não uma FK."""

    __tablename__ = "rustdesk_peers"

    id = Column(Integer, primary_key=True, index=True)
    rustdesk_id = Column(String(253), nullable=False, unique=True, index=True)
    hostname = Column(String(255), nullable=True)
    username = Column(String(255), nullable=True)
    sistema = Column(String(120), nullable=True)
    ip = Column(String(64), nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
