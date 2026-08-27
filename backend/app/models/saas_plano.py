"""Catálogo comercial de planos e módulos SaaS (control-plane) — v1 sem enforcement hard na instância."""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class SaasModulo(Base):
    __tablename__ = "saas_modulos"
    __table_args__ = (UniqueConstraint("codigo", name="uq_saas_modulos_codigo"),)

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(80), nullable=False, index=True)
    nome = Column(String(120), nullable=False)
    descricao = Column(Text, nullable=True)
    preco_mensal = Column(Numeric(12, 2), nullable=True)
    ativo = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    planos = relationship("SaasPlanoModulo", back_populates="modulo", cascade="all, delete-orphan")


class SaasPlano(Base):
    __tablename__ = "saas_planos"
    __table_args__ = (UniqueConstraint("codigo", name="uq_saas_planos_codigo"),)

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(80), nullable=False, index=True)
    nome = Column(String(120), nullable=False)
    descricao = Column(Text, nullable=True)
    ativo = Column(Boolean, nullable=False, default=True)
    ordem = Column(Integer, nullable=False, default=0)
    preco_mensal = Column(Numeric(12, 2), nullable=True)
    # Usuários inclusos no preço dos módulos (padrão 3).
    usuarios_inclusos = Column(Integer, nullable=False, default=3, server_default="3")
    preco_usuario_extra = Column(Numeric(12, 2), nullable=True)
    max_postos = Column(Integer, nullable=True)
    max_usuarios = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    modulos_links = relationship(
        "SaasPlanoModulo",
        back_populates="plano",
        cascade="all, delete-orphan",
        order_by="SaasPlanoModulo.modulo_id",
    )


class SaasPlanoModulo(Base):
    __tablename__ = "saas_plano_modulos"
    __table_args__ = (UniqueConstraint("plano_id", "modulo_id", name="uq_saas_plano_modulo"),)

    plano_id = Column(Integer, ForeignKey("saas_planos.id", ondelete="CASCADE"), primary_key=True)
    modulo_id = Column(Integer, ForeignKey("saas_modulos.id", ondelete="CASCADE"), primary_key=True)

    plano = relationship("SaasPlano", back_populates="modulos_links")
    modulo = relationship("SaasModulo", back_populates="planos")
