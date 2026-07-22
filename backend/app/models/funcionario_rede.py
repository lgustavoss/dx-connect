from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class TipoFuncionarioRede(str, enum.Enum):
    socio = "socio"       # vinculado à rede (pode ser mais de 1 por rede)
    supervisor = "supervisor"  # vinculado a várias empresas
    colaborador = "colaborador"  # vinculado a uma empresa


class FuncionarioRede(Base):
    """Pessoa do lado do cliente: sócio da rede, supervisor (várias empresas) ou colaborador (uma empresa)."""

    __tablename__ = "funcionarios_rede"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True, index=True)  # opcional (#444); único por rede quando preenchido
    telefone = Column(String(20), nullable=True, index=True)  # WhatsApp (#531); só dígitos
    tipo = Column(String(20), nullable=False)  # socio | supervisor | colaborador
    escopo_empresas = Column(String(20), nullable=False, default="selected")  # all | selected
    ativo = Column(Boolean, default=True)
    # Auth do portal do cliente (#263 / #300)
    senha_hash = Column(String(255), nullable=True)
    must_change_password = Column(Boolean, default=False, nullable=False)
    token_version = Column(Integer, default=0, nullable=False)
    notificar_email_portal = Column(Boolean, default=True, nullable=False)
    # Sócio: preenchido rede_id
    rede_id = Column(Integer, ForeignKey("redes.id"), nullable=True)
    # Colaborador: preenchido empresa_id
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    rede = relationship("Rede", back_populates="socios", foreign_keys=[rede_id])
    empresa = relationship("Empresa", back_populates="colaboradores", foreign_keys=[empresa_id])
    empresas_supervisor = relationship("FuncionarioRedeEmpresa", back_populates="funcionario", foreign_keys="FuncionarioRedeEmpresa.funcionario_id")
    tickets_abertos = relationship("Ticket", back_populates="aberto_por")


class FuncionarioRedeEmpresa(Base):
    """Supervisor: N:N com empresas."""

    __tablename__ = "funcionario_rede_empresa"

    id = Column(Integer, primary_key=True, index=True)
    funcionario_id = Column(Integer, ForeignKey("funcionarios_rede.id", ondelete="CASCADE"), nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False)

    funcionario = relationship("FuncionarioRede", back_populates="empresas_supervisor", foreign_keys=[funcionario_id])
    empresa = relationship("Empresa", back_populates="empresas_supervisor", foreign_keys=[empresa_id])
