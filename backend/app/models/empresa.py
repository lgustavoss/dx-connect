from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    rede_id = Column(Integer, ForeignKey("redes.id"), nullable=False)
    tipo_negocio_id = Column(Integer, ForeignKey("tipos_negocio.id"), nullable=True)
    nome = Column(String(255), nullable=False)
    cnpj_cpf = Column(String(18), nullable=True, index=True)
    razao_social = Column(String(255), nullable=True)
    nome_fantasia = Column(String(255), nullable=True)
    inscricao_estadual = Column(String(20), nullable=True)
    endereco = Column(String(255), nullable=True)
    numero = Column(String(20), nullable=True)
    complemento = Column(String(100), nullable=True)
    bairro = Column(String(100), nullable=True)
    cidade = Column(String(100), nullable=True)
    estado = Column(String(2), nullable=True)
    cep = Column(String(10), nullable=True)
    email = Column(String(255), nullable=True)
    telefone = Column(String(20), nullable=True)
    # Responsável legal (contratos / procurações)
    resp_legal_nome = Column(String(255), nullable=True)
    resp_legal_cpf = Column(String(14), nullable=True)
    resp_legal_rg = Column(String(20), nullable=True)
    resp_legal_orgao_emissor = Column(String(30), nullable=True)
    resp_legal_nacionalidade = Column(String(50), nullable=True)
    resp_legal_estado_civil = Column(String(30), nullable=True)
    resp_legal_cargo = Column(String(100), nullable=True)
    resp_legal_email = Column(String(255), nullable=True)
    resp_legal_telefone = Column(String(20), nullable=True)
    resp_legal_endereco = Column(String(255), nullable=True)
    resp_legal_numero = Column(String(20), nullable=True)
    resp_legal_complemento = Column(String(100), nullable=True)
    resp_legal_bairro = Column(String(100), nullable=True)
    resp_legal_cidade = Column(String(100), nullable=True)
    resp_legal_estado = Column(String(2), nullable=True)
    resp_legal_cep = Column(String(10), nullable=True)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    rede = relationship("Rede", back_populates="empresas")
    tipo_negocio = relationship("TipoNegocio", back_populates="empresas")
    tickets = relationship("Ticket", back_populates="empresa")
    colaboradores = relationship("FuncionarioRede", back_populates="empresa", foreign_keys="FuncionarioRede.empresa_id")
    empresas_supervisor = relationship("FuncionarioRedeEmpresa", back_populates="empresa", foreign_keys="FuncionarioRedeEmpresa.empresa_id")
