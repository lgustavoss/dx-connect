"""Tabela de tokens para redefinição de senha (#105).

Revision ID: 030_password_reset_tokens
Revises: 029_merge_ticket_parent_outbox
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa

revision = "030_password_reset_tokens"
down_revision = "029_merge_ticket_parent_outbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("atendente_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["atendente_id"], ["atendentes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_password_reset_tokens_atendente_id", "password_reset_tokens", ["atendente_id"])
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_token_hash", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_atendente_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
