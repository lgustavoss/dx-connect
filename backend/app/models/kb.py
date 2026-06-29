"""Base de conhecimento — categorias e artigos."""

import enum

from sqlalchemy import (
    Boolean,
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
    interno_only = Column(Boolean, nullable=False, server_default="false", default=False)
    autor_atendente_id = Column(Integer, ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True, index=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    category = relationship("KbCategory", back_populates="articles")
    autor = relationship("Atendente", foreign_keys=[autor_atendente_id])
    versions = relationship("KbArticleVersion", back_populates="article", order_by="KbArticleVersion.id.desc()")
    motivo_links = relationship(
        "KbArticleMotivoLink",
        back_populates="article",
        cascade="all, delete-orphan",
        order_by="KbArticleMotivoLink.ordem",
    )


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
    autor = relationship("Atendente", foreign_keys=[autor_atendente_id])


class KbArticleMotivoLink(Base):
    __tablename__ = "kb_article_motivo_links"
    __table_args__ = (
        UniqueConstraint("article_id", "motivo_id", name="uq_kb_article_motivo_links_article_motivo"),
        UniqueConstraint("article_id", "natureza_id", name="uq_kb_article_motivo_links_article_natureza"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    article_id = Column(Integer, ForeignKey("kb_articles.id", ondelete="CASCADE"), nullable=False, index=True)
    motivo_id = Column(Integer, ForeignKey("ticket_motivos.id", ondelete="CASCADE"), nullable=True, index=True)
    natureza_id = Column(Integer, ForeignKey("ticket_naturezas.id", ondelete="CASCADE"), nullable=True, index=True)
    ordem = Column(SmallInteger, default=0, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    article = relationship("KbArticle", back_populates="motivo_links")
    motivo = relationship("TicketMotivo")
    natureza = relationship("TicketNatureza")


class KbPortalSettings(Base):
    """Personalização visual do portal público /kb (#467)."""

    __tablename__ = "kb_portal_settings"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_kb_portal_settings_tenant_id"),)

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    portal_titulo = Column(String(120), nullable=True)
    texto_boas_vindas = Column(String(500), nullable=True)
    cor_header = Column(String(7), nullable=False, server_default="#0B2D4A", default="#0B2D4A")
    cor_primaria = Column(String(7), nullable=False, server_default="#0D9488", default="#0D9488")
    cor_texto_header = Column(String(7), nullable=False, server_default="#FFFFFF", default="#FFFFFF")
    cor_texto_corpo = Column(String(7), nullable=False, server_default="#0F172A", default="#0F172A")
    cor_fundo = Column(String(7), nullable=False, server_default="#F8FAFC", default="#F8FAFC")
    cor_link = Column(String(7), nullable=True)
    exibir_marca_deskrudder = Column(Boolean, nullable=False, server_default="true", default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
