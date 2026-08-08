"""Catálogo comercial de custos e salário mínimo (#321 / #329–#330)."""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.database import Base

# Tipos de item do catálogo (lote A; composto_tef usado no motor/simular)
TIPO_PERCENTUAL_SM = "percentual_sm"
TIPO_VALOR_FIXO = "valor_fixo"
TIPO_COMPOSTO_TEF = "composto_tef"
TIPOS_CUSTO_CATALOGO = frozenset({TIPO_PERCENTUAL_SM, TIPO_VALOR_FIXO, TIPO_COMPOSTO_TEF})


class SalarioMinimoReferencia(Base):
    """Salário mínimo com vigência — contratos futuros usam snapshot, não recalculam (#329)."""

    __tablename__ = "salario_minimo_referencia"

    id = Column(Integer, primary_key=True, index=True)
    valor = Column(Numeric(12, 2), nullable=False)
    vigencia_inicio = Column(Date, nullable=False, index=True)
    vigencia_fim = Column(Date, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class CustoCatalogoItem(Base):
    """Perfil/módulo de custo cadastrável (#330)."""

    __tablename__ = "custo_catalogo_itens"
    __table_args__ = (UniqueConstraint("slug", name="uq_custo_catalogo_item_slug"),)

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    slug = Column(String(50), nullable=False, index=True)
    descricao = Column(Text, nullable=True)
    tipo = Column(String(24), nullable=False, index=True)
    percentual_sm = Column(Numeric(8, 4), nullable=True)
    valor_fixo = Column(Numeric(12, 2), nullable=True)
    tef_base = Column(Numeric(12, 2), nullable=True)
    tef_adicional = Column(Numeric(12, 2), nullable=True)
    ordem = Column(Integer, default=0, nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    vigencia_inicio = Column(Date, nullable=True)
    vigencia_fim = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
