from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Rede(Base):
    __tablename__ = "redes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False)
    login_retaguarda = Column(String(120), nullable=True)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    empresas = relationship("Empresa", back_populates="rede")
    socios = relationship("FuncionarioRede", back_populates="rede", foreign_keys="FuncionarioRede.rede_id")
