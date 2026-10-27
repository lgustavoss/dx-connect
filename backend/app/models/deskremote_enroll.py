from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class DeskremoteInstallToken(Base):
    __tablename__ = "deskremote_install_tokens"

    id = Column(Integer, primary_key=True, index=True)
    pdv_id = Column(Integer, ForeignKey("empresa_pdvs.id", ondelete="CASCADE"), nullable=False, index=True)
    acesso_id = Column(
        Integer,
        ForeignKey("empresa_pdv_acessos_remotos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_by_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    pdv = relationship("EmpresaPdv")
    acesso = relationship("EmpresaPdvAcessoRemoto")


class DeskremoteDispositivo(Base):
    __tablename__ = "deskremote_dispositivos"

    id = Column(Integer, primary_key=True, index=True)
    pdv_id = Column(Integer, ForeignKey("empresa_pdvs.id", ondelete="CASCADE"), nullable=False, index=True)
    acesso_id = Column(
        Integer,
        ForeignKey("empresa_pdv_acessos_remotos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    rustdesk_id = Column(String(64), nullable=True)
    senha_versao_aplicada = Column(Integer, nullable=False, default=0)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    pdv = relationship("EmpresaPdv")
    acesso = relationship("EmpresaPdvAcessoRemoto")
