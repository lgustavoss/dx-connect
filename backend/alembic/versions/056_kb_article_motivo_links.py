"""KB: vínculos artigo ↔ natureza/motivo (#296).

Revision ID: 056_kb_motivo_links
Revises: 055_func_rede_email_null
Create Date: 2026-06-29
"""

import sqlalchemy as sa
from alembic import op

revision = "056_kb_motivo_links"
down_revision = "055_func_rede_email_null"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "kb_article_motivo_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("motivo_id", sa.Integer(), nullable=True),
        sa.Column("natureza_id", sa.Integer(), nullable=True),
        sa.Column("ordem", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.CheckConstraint(
            "(motivo_id IS NOT NULL) OR (natureza_id IS NOT NULL)",
            name="ck_kb_article_motivo_links_target",
        ),
        sa.ForeignKeyConstraint(["article_id"], ["kb_articles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["motivo_id"], ["ticket_motivos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["natureza_id"], ["ticket_naturezas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("article_id", "motivo_id", name="uq_kb_article_motivo_links_article_motivo"),
        sa.UniqueConstraint(
            "article_id",
            "natureza_id",
            name="uq_kb_article_motivo_links_article_natureza",
        ),
    )
    op.create_index("ix_kb_article_motivo_links_tenant_id", "kb_article_motivo_links", ["tenant_id"])
    op.create_index("ix_kb_article_motivo_links_article_id", "kb_article_motivo_links", ["article_id"])
    op.create_index("ix_kb_article_motivo_links_motivo_id", "kb_article_motivo_links", ["motivo_id"])
    op.create_index("ix_kb_article_motivo_links_natureza_id", "kb_article_motivo_links", ["natureza_id"])


def downgrade() -> None:
    op.drop_table("kb_article_motivo_links")
