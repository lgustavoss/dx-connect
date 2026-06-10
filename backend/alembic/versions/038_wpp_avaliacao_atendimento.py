"""WhatsApp: avaliação 1–5 ao encerrar atendimento.

Revision ID: 038_wpp_avaliacao
Revises: 037_wpp_inatividade
Create Date: 2026-06-09
"""

from alembic import op
import sqlalchemy as sa

revision = "038_wpp_avaliacao"
down_revision = "037_wpp_inatividade"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "whatsapp_settings",
        sa.Column("avaliacao_ativa", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "whatsapp_settings",
        sa.Column("auto_msg_avaliacao_ativa", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column("whatsapp_settings", sa.Column("auto_msg_avaliacao_texto", sa.Text(), nullable=True))
    op.add_column("whatsapp_settings", sa.Column("auto_msg_avaliacao_obrigado_texto", sa.Text(), nullable=True))
    op.add_column("whatsapp_chats", sa.Column("avaliacao_nota", sa.Integer(), nullable=True))
    op.add_column("whatsapp_chats", sa.Column("avaliacao_respondida_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("whatsapp_settings", "avaliacao_ativa", server_default=None)
    op.alter_column("whatsapp_settings", "auto_msg_avaliacao_ativa", server_default=None)


def downgrade() -> None:
    op.drop_column("whatsapp_chats", "avaliacao_respondida_at")
    op.drop_column("whatsapp_chats", "avaliacao_nota")
    op.drop_column("whatsapp_settings", "auto_msg_avaliacao_obrigado_texto")
    op.drop_column("whatsapp_settings", "auto_msg_avaliacao_texto")
    op.drop_column("whatsapp_settings", "auto_msg_avaliacao_ativa")
    op.drop_column("whatsapp_settings", "avaliacao_ativa")
