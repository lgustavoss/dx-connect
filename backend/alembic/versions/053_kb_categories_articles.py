"""Base de conhecimento — categorias e artigos (#262 KB-F1).

Revision ID: 053_kb_categories_articles
Revises: 052_audit_log_expandido
Create Date: 2026-06-24
"""

import sqlalchemy as sa
from alembic import op

revision = "053_kb_categories_articles"
down_revision = "052_audit_log_expandido"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "kb_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("ordem", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["parent_id"], ["kb_categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_kb_categories_tenant_slug"),
    )
    op.create_index(op.f("ix_kb_categories_id"), "kb_categories", ["id"], unique=False)
    op.create_index(op.f("ix_kb_categories_slug"), "kb_categories", ["slug"], unique=False)
    op.create_index(op.f("ix_kb_categories_tenant_id"), "kb_categories", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_kb_categories_parent_id"), "kb_categories", ["parent_id"], unique=False)

    op.create_table(
        "kb_articles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="rascunho",
            nullable=False,
        ),
        sa.Column("conteudo_markdown", sa.Text(), server_default="", nullable=False),
        sa.Column("autor_atendente_id", sa.Integer(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["autor_atendente_id"], ["atendentes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["category_id"], ["kb_categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_kb_articles_tenant_slug"),
    )
    op.create_index(op.f("ix_kb_articles_id"), "kb_articles", ["id"], unique=False)
    op.create_index(op.f("ix_kb_articles_slug"), "kb_articles", ["slug"], unique=False)
    op.create_index(op.f("ix_kb_articles_tenant_id"), "kb_articles", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_kb_articles_category_id"), "kb_articles", ["category_id"], unique=False)
    op.create_index(op.f("ix_kb_articles_status"), "kb_articles", ["status"], unique=False)
    op.create_index(op.f("ix_kb_articles_autor_atendente_id"), "kb_articles", ["autor_atendente_id"], unique=False)

    op.create_table(
        "kb_article_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(length=255), nullable=False),
        sa.Column("conteudo_markdown", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("autor_atendente_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["article_id"], ["kb_articles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["autor_atendente_id"], ["atendentes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_kb_article_versions_id"), "kb_article_versions", ["id"], unique=False)
    op.create_index(op.f("ix_kb_article_versions_article_id"), "kb_article_versions", ["article_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_kb_article_versions_article_id"), table_name="kb_article_versions")
    op.drop_index(op.f("ix_kb_article_versions_id"), table_name="kb_article_versions")
    op.drop_table("kb_article_versions")
    op.drop_index(op.f("ix_kb_articles_autor_atendente_id"), table_name="kb_articles")
    op.drop_index(op.f("ix_kb_articles_status"), table_name="kb_articles")
    op.drop_index(op.f("ix_kb_articles_category_id"), table_name="kb_articles")
    op.drop_index(op.f("ix_kb_articles_tenant_id"), table_name="kb_articles")
    op.drop_index(op.f("ix_kb_articles_slug"), table_name="kb_articles")
    op.drop_index(op.f("ix_kb_articles_id"), table_name="kb_articles")
    op.drop_table("kb_articles")
    op.drop_index(op.f("ix_kb_categories_parent_id"), table_name="kb_categories")
    op.drop_index(op.f("ix_kb_categories_tenant_id"), table_name="kb_categories")
    op.drop_index(op.f("ix_kb_categories_slug"), table_name="kb_categories")
    op.drop_index(op.f("ix_kb_categories_id"), table_name="kb_categories")
    op.drop_table("kb_categories")
