from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PdvRotulo(Base):
    __tablename__ = "pdv_rotulos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    ordem_exibicao = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    pdvs = relationship("EmpresaPdv", back_populates="rotulo")


class PdvTipoAcessoRemoto(Base):
    __tablename__ = "pdv_tipos_acesso_remoto"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    ordem_exibicao = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    pdvs = relationship("EmpresaPdv", back_populates="tipo_acesso_remoto")


class EmpresaPdv(Base):
    __tablename__ = "empresa_pdvs"
    __table_args__ = (UniqueConstraint("empresa_id", "codigo", name="uq_empresa_pdv_codigo"),)

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True)
    codigo = Column(String(32), nullable=False)
    rotulo_id = Column(Integer, ForeignKey("pdv_rotulos.id"), nullable=False)
    papel = Column(String(20), nullable=False)  # principal | auxiliar
    usa_tef = Column(Boolean, default=False, nullable=False)
    tipo_acesso_remoto_id = Column(Integer, ForeignKey("pdv_tipos_acesso_remoto.id"), nullable=True)
    acesso_remoto_id = Column(String(255), nullable=True)
    acesso_remoto_senha_cifrada = Column(Text, nullable=True)
    observacoes = Column(Text, nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    empresa = relationship("Empresa", back_populates="pdvs")
    rotulo = relationship("PdvRotulo", back_populates="pdvs")
    tipo_acesso_remoto = relationship("PdvTipoAcessoRemoto", back_populates="pdvs")
