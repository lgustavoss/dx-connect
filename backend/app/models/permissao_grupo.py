from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

atendente_permissao_grupo = Table(
    "atendente_permissao_grupo",
    Base.metadata,
    Column("atendente_id", Integer, ForeignKey("atendentes.id", ondelete="CASCADE"), primary_key=True),
    Column("grupo_id", Integer, ForeignKey("permissao_grupos.id", ondelete="CASCADE"), primary_key=True),
)


class PermissaoGrupo(Base):
    """Grupo de permissão da instância. O perfil interno (role) sai da união dos grupos da pessoa."""

    __tablename__ = "permissao_grupos"
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_permissao_grupos_tenant_slug"),)

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    nome = Column(String(120), nullable=False)
    slug = Column(String(80), nullable=False)
    sistema = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    itens = relationship(
        "PermissaoGrupoItem",
        back_populates="grupo",
        cascade="all, delete-orphan",
    )
    atendentes = relationship(
        "Atendente",
        secondary=atendente_permissao_grupo,
        back_populates="grupos_permissao",
    )


class PermissaoGrupoItem(Base):
    __tablename__ = "permissao_grupo_itens"

    grupo_id = Column(Integer, ForeignKey("permissao_grupos.id", ondelete="CASCADE"), primary_key=True)
    codigo = Column(String(40), primary_key=True)

    grupo = relationship("PermissaoGrupo", back_populates="itens")
