"""Tabela de sequência mensal para protocolos #T / #C e alarga tickets.protocolo.

Revision ID: 017_protocol_sequences
Revises: 016_ticket_anexos
Create Date: 2026-05-13
"""

from alembic import op
import sqlalchemy as sa


revision = "017_protocol_sequences"
down_revision = "016_ticket_anexos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("protocol_sequences"):
        op.create_table(
            "protocol_sequences",
            sa.Column("kind", sa.String(length=1), nullable=False),
            sa.Column("ano_mes", sa.String(length=7), nullable=False),
            sa.Column("last_value", sa.Integer(), nullable=False, server_default="0"),
            sa.PrimaryKeyConstraint("kind", "ano_mes", name="pk_protocol_sequences"),
        )
    cols = {c["name"] for c in insp.get_columns("tickets")} if insp.has_table("tickets") else set()
    if "protocolo" in cols:
        op.alter_column(
            "tickets",
            "protocolo",
            existing_type=sa.String(length=20),
            type_=sa.String(length=32),
            existing_nullable=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("protocol_sequences"):
        op.drop_table("protocol_sequences")
    if insp.has_table("tickets"):
        op.alter_column(
            "tickets",
            "protocolo",
            existing_type=sa.String(length=32),
            type_=sa.String(length=20),
            existing_nullable=False,
        )
