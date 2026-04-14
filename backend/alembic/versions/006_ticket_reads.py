"""Tabela ticket_reads e índice em ticket_mensagens.

Revision ID: 006_ticket_reads
Revises: 005_rede_login_retaguarda
Create Date: 2026-04-14
"""

from alembic import op
import sqlalchemy as sa


revision = "006_ticket_reads"
down_revision = "005_rede_login_retaguarda"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ticket_reads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("atendente_id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["atendente_id"], ["atendentes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("atendente_id", "ticket_id", name="uq_ticket_reads_atendente_ticket"),
    )
    op.create_index(op.f("ix_ticket_reads_id"), "ticket_reads", ["id"], unique=False)
    op.create_index(op.f("ix_ticket_reads_atendente_id"), "ticket_reads", ["atendente_id"], unique=False)
    op.create_index(op.f("ix_ticket_reads_ticket_id"), "ticket_reads", ["ticket_id"], unique=False)
    op.create_index(
        "ix_ticket_mensagens_ticket_id_created_at",
        "ticket_mensagens",
        ["ticket_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ticket_mensagens_ticket_id_created_at", table_name="ticket_mensagens")
    op.drop_index(op.f("ix_ticket_reads_ticket_id"), table_name="ticket_reads")
    op.drop_index(op.f("ix_ticket_reads_atendente_id"), table_name="ticket_reads")
    op.drop_index(op.f("ix_ticket_reads_id"), table_name="ticket_reads")
    op.drop_table("ticket_reads")
