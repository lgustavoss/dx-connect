"""KB portal: avaliação útil/não útil em artigos (#469).

Revision ID: 064_kb_article_feedback
Revises: 063_chat_interno_grupos
Create Date: 2026-07-11
"""

import sqlalchemy as sa
from alembic import op

revision = "064_kb_article_feedback"
down_revision = "063_chat_interno_grupos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "kb_articles",
        sa.Column("feedback_util_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "kb_articles",
        sa.Column("feedback_nao_util_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "kb_portal_settings",
        sa.Column("feedback_habilitado", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.create_table(
        "kb_article_feedback_votes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("ip_hash", sa.String(length=64), nullable=False),
        sa.Column("util", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["article_id"], ["kb_articles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("article_id", "ip_hash", name="uq_kb_article_feedback_votes_article_ip"),
    )
    op.create_index(
        "ix_kb_article_feedback_votes_article_id",
        "kb_article_feedback_votes",
        ["article_id"],
    )
    op.create_index(
        "ix_kb_article_feedback_votes_tenant_id",
        "kb_article_feedback_votes",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_kb_article_feedback_votes_tenant_id", table_name="kb_article_feedback_votes")
    op.drop_index("ix_kb_article_feedback_votes_article_id", table_name="kb_article_feedback_votes")
    op.drop_table("kb_article_feedback_votes")
    op.drop_column("kb_portal_settings", "feedback_habilitado")
    op.drop_column("kb_articles", "feedback_nao_util_count")
    op.drop_column("kb_articles", "feedback_util_count")
