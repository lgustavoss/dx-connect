"""Portal chat: demandas e evento_sistema nas mensagens.

Revision ID: 066_portal_chat_demandas
Revises: 065_portal_chat
Create Date: 2026-07-12
"""

import sqlalchemy as sa
from alembic import op

revision = "066_portal_chat_demandas"
down_revision = "065_portal_chat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portal_mensagens",
        sa.Column("evento_sistema", sa.String(length=40), nullable=True),
    )

    op.create_table(
        "portal_chat_demandas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chat_id", sa.Integer(), nullable=False),
        sa.Column("natureza_id", sa.Integer(), nullable=False),
        sa.Column("motivo_id", sa.Integer(), nullable=True),
        sa.Column("desfecho", sa.String(length=24), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=True),
        sa.Column("descricao_curta", sa.String(length=500), nullable=True),
        sa.Column("atendente_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["atendente_id"], ["atendentes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["chat_id"], ["portal_chats.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["motivo_id"], ["ticket_motivos.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["natureza_id"], ["ticket_naturezas.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_portal_chat_demandas_chat_id", "portal_chat_demandas", ["chat_id"])
    op.create_index("ix_portal_chat_demandas_desfecho", "portal_chat_demandas", ["desfecho"])
    op.create_index("ix_portal_chat_demandas_natureza_id", "portal_chat_demandas", ["natureza_id"])
    op.create_index("ix_portal_chat_demandas_motivo_id", "portal_chat_demandas", ["motivo_id"])
    op.create_index("ix_portal_chat_demandas_ticket_id", "portal_chat_demandas", ["ticket_id"])
    op.create_index("ix_portal_chat_demandas_atendente_id", "portal_chat_demandas", ["atendente_id"])


def downgrade() -> None:
    op.drop_table("portal_chat_demandas")
    op.drop_column("portal_mensagens", "evento_sistema")
