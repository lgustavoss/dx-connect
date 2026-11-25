"""Pool Boleto Cloud, vínculo cliente→pool e contas bancárias (#1392)."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

BOLETO_CLOUD_URL_SANDBOX = "https://sandbox.boletocloud.com/api/v1"


class BoletoPool(Base):
    """Uma conta (login/API Key) no Boleto Cloud = um pool de cobrança."""

    __tablename__ = "boleto_pools"

    id = Column(Integer, primary_key=True, index=True)
    apelido = Column(String(120), nullable=False)
    email_login = Column(String(255), nullable=True)
    api_base_url = Column(String(255), nullable=False, default=BOLETO_CLOUD_URL_SANDBOX)
    api_key_cifrada = Column(Text, nullable=True)
    # Legado do piloto (token único no pool). Preferir cobranca_contas_bancarias.
    conta_token_cifrado = Column(Text, nullable=True)
    faixa_teto = Column(Integer, nullable=True)
    notas = Column(Text, nullable=True)
    ativo = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    vinculos = relationship("BoletoPoolVinculo", back_populates="pool")


class BoletoPoolVinculo(Base):
    """Cliente SaaS alocado a um pool. Vigência define qual pool vale para emissão nova.

    Boletos já emitidos permanecem na conta BC de origem — a migração não os move.
    """

    __tablename__ = "boleto_pool_vinculos"

    id = Column(Integer, primary_key=True, index=True)
    cliente_saas_id = Column(
        Integer,
        ForeignKey("clientes_saas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pool_id = Column(
        Integer,
        ForeignKey("boleto_pools.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    vigencia_de = Column(DateTime(timezone=True), nullable=False)
    vigencia_ate = Column(DateTime(timezone=True), nullable=True)
    notas = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    pool = relationship("BoletoPool", back_populates="vinculos")
    cliente = relationship("ClienteSaaS")


class CobrancaContaBancaria(Base):
    """Conta bancária cedente cadastrada na instância (dados + token BC)."""

    __tablename__ = "cobranca_contas_bancarias"

    id = Column(Integer, primary_key=True, index=True)
    apelido = Column(String(120), nullable=False)
    banco_codigo = Column(String(10), nullable=True)
    banco_nome = Column(String(120), nullable=True)
    agencia = Column(String(20), nullable=True)
    agencia_dv = Column(String(4), nullable=True)
    conta = Column(String(32), nullable=True)
    conta_dv = Column(String(4), nullable=True)
    carteira = Column(String(20), nullable=True)
    titular_nome = Column(String(200), nullable=True)
    titular_documento = Column(String(20), nullable=True)
    boleto_cloud_token_cifrado = Column(Text, nullable=True)
    ativo = Column(Boolean, nullable=False, default=True)
    padrao = Column(Boolean, nullable=False, default=False)
    notas = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
