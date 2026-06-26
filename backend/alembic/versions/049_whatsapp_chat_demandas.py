"""WhatsApp: demandas registradas por sessão de chat (#423).

Revision ID: 049_whatsapp_chat_demandas
Revises: 048_sla_alertas
Create Date: 2026-06-23
"""

import sqlalchemy as sa
from alembic import op

revision = "049_whatsapp_chat_demandas"
down_revision = "048_sla_alertas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "whatsapp_chat_demandas",
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
        sa.ForeignKeyConstraint(["chat_id"], ["whatsapp_chats.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["motivo_id"], ["ticket_motivos.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["natureza_id"], ["ticket_naturezas.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_whatsapp_chat_demandas_id"), "whatsapp_chat_demandas", ["id"], unique=False)
    op.create_index(op.f("ix_whatsapp_chat_demandas_chat_id"), "whatsapp_chat_demandas", ["chat_id"], unique=False)
    op.create_index(op.f("ix_whatsapp_chat_demandas_natureza_id"), "whatsapp_chat_demandas", ["natureza_id"], unique=False)
    op.create_index(op.f("ix_whatsapp_chat_demandas_motivo_id"), "whatsapp_chat_demandas", ["motivo_id"], unique=False)
    op.create_index(op.f("ix_whatsapp_chat_demandas_desfecho"), "whatsapp_chat_demandas", ["desfecho"], unique=False)
    op.create_index(op.f("ix_whatsapp_chat_demandas_ticket_id"), "whatsapp_chat_demandas", ["ticket_id"], unique=False)
    op.create_index(op.f("ix_whatsapp_chat_demandas_atendente_id"), "whatsapp_chat_demandas", ["atendente_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_whatsapp_chat_demandas_atendente_id"), table_name="whatsapp_chat_demandas")
    op.drop_index(op.f("ix_whatsapp_chat_demandas_ticket_id"), table_name="whatsapp_chat_demandas")
    op.drop_index(op.f("ix_whatsapp_chat_demandas_desfecho"), table_name="whatsapp_chat_demandas")
    op.drop_index(op.f("ix_whatsapp_chat_demandas_motivo_id"), table_name="whatsapp_chat_demandas")
    op.drop_index(op.f("ix_whatsapp_chat_demandas_natureza_id"), table_name="whatsapp_chat_demandas")
    op.drop_index(op.f("ix_whatsapp_chat_demandas_chat_id"), table_name="whatsapp_chat_demandas")
    op.drop_index(op.f("ix_whatsapp_chat_demandas_id"), table_name="whatsapp_chat_demandas")
    op.drop_table("whatsapp_chat_demandas")
