"""Tickets: anexos (upload/download).

Revision ID: 016_ticket_anexos
Revises: 015_wpp_citacao
Create Date: 2026-04-25
"""

from alembic import op
import sqlalchemy as sa


revision = "016_ticket_anexos"
down_revision = "015_wpp_citacao"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("ticket_anexos"):
        op.create_table(
            "ticket_anexos",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("ticket_id", sa.Integer(), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
            sa.Column(
                "mensagem_id",
                sa.Integer(),
                sa.ForeignKey("ticket_mensagens.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "atendente_id",
                sa.Integer(),
                sa.ForeignKey("atendentes.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("visibilidade", sa.String(length=20), nullable=False, server_default="publico"),
            sa.Column("nome_original", sa.String(length=255), nullable=False),
            sa.Column("content_type", sa.String(length=128), nullable=True),
            sa.Column("tamanho_bytes", sa.Integer(), nullable=False),
            sa.Column("storage_key", sa.String(length=500), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_ticket_anexos_ticket_id", "ticket_anexos", ["ticket_id"])
        op.create_index("ix_ticket_anexos_mensagem_id", "ticket_anexos", ["mensagem_id"])
        op.create_index("ix_ticket_anexos_atendente_id", "ticket_anexos", ["atendente_id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("ticket_anexos"):
        return
    op.drop_index("ix_ticket_anexos_atendente_id", table_name="ticket_anexos")
    op.drop_index("ix_ticket_anexos_mensagem_id", table_name="ticket_anexos")
    op.drop_index("ix_ticket_anexos_ticket_id", table_name="ticket_anexos")
    op.drop_table("ticket_anexos")

