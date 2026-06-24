"""Base de conhecimento — categorias e artigos."""

import enum

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class KbArticleStatus(str, enum.Enum):
    rascunho = "rascunho"
    publicado = "publicado"
    arquivado = "arquivado"


class KbCategory(Base):
    __tablename__ = "kb_categories"
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_kb_categories_tenant_slug"),)

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    nome = Column(String(120), nullable=False)
    slug = Column(String(80), nullable=False, index=True)
    ordem = Column(SmallInteger, default=0, nullable=False)
    parent_id = Column(Integer, ForeignKey("kb_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    parent = relationship("KbCategory", remote_side="KbCategory.id", backref="children")
    articles = relationship("KbArticle", back_populates="category")


class KbArticle(Base):
    __tablename__ = "kb_articles"
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_kb_articles_tenant_slug"),)

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    titulo = Column(String(255), nullable=False)
    slug = Column(String(120), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("kb_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(
        SAEnum(KbArticleStatus, name="kb_article_status", native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        server_default=KbArticleStatus.rascunho.value,
        index=True,
    )
    conteudo_markdown = Column(Text, nullable=False, server_default="")
    autor_atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True, index=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    category = relationship("KbCategory", back_populates="articles")
    autor = relationship("Atendente", foreign_keys=[autor_atendente_id])
    versions = relationship("KbArticleVersion", back_populates="article", order_by="KbArticleVersion.id.desc()")


class KbArticleVersion(Base):
    __tablename__ = "kb_article_versions"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("kb_articles.id", ondelete="CASCADE"), nullable=False, index=True)
    titulo = Column(String(255), nullable=False)
    conteudo_markdown = Column(Text, nullable=False)
    status = Column(String(20), nullable=False)
    autor_atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    article = relationship("KbArticle", back_populates="versions")
