from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class EmpresaSistema(Base):
    """
    Singleton (1 linha) com dados da empresa do sistema.
    Regras de unicidade são aplicadas pela API (primeira linha é a "empresa do sistema").
    """

    __tablename__ = "empresa_sistema"

    id = Column(Integer, primary_key=True, index=True)
    cnpj = Column(String(18), nullable=True, index=True)
    nome = Column(String(255), nullable=True)
    razao_social = Column(String(255), nullable=True)
    nome_fantasia = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    telefone = Column(String(20), nullable=True)
    endereco = Column(String(255), nullable=True)
    numero = Column(String(20), nullable=True)
    complemento = Column(String(100), nullable=True)
    bairro = Column(String(100), nullable=True)
    cidade = Column(String(100), nullable=True)
    estado = Column(String(2), nullable=True)
    cep = Column(String(10), nullable=True)
    # Pin do local de trabalho da empresa (#984).
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    ponto_raio_metros = Column(Integer, nullable=False, default=200, server_default="200")
    logo_filename = Column(String(255), nullable=True)
    logo_mimetype = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

