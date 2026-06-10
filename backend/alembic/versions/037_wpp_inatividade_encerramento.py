"""WhatsApp: encerramento automático por inatividade do cliente.

Revision ID: 037_wpp_inatividade
Revises: 036_ticket_classificacao
Create Date: 2026-06-09
"""

from alembic import op
import sqlalchemy as sa

revision = "037_wpp_inatividade"
down_revision = "036_ticket_classificacao"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "whatsapp_settings",
        sa.Column("inativ_encerramento_ativa", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "whatsapp_settings",
        sa.Column("inativ_aviso_minutos", sa.Integer(), nullable=True),
    )
    op.add_column(
        "whatsapp_settings",
        sa.Column("inativ_encerramento_apos_aviso_minutos", sa.Integer(), nullable=True),
    )
    op.add_column(
        "whatsapp_settings",
        sa.Column("auto_msg_inativ_aviso_ativa", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "whatsapp_settings",
        sa.Column("auto_msg_inativ_aviso_texto", sa.Text(), nullable=True),
    )
    op.alter_column("whatsapp_settings", "inativ_encerramento_ativa", server_default=None)
    op.alter_column("whatsapp_settings", "auto_msg_inativ_aviso_ativa", server_default=None)


def downgrade() -> None:
    op.drop_column("whatsapp_settings", "auto_msg_inativ_aviso_texto")
    op.drop_column("whatsapp_settings", "auto_msg_inativ_aviso_ativa")
    op.drop_column("whatsapp_settings", "inativ_encerramento_apos_aviso_minutos")
    op.drop_column("whatsapp_settings", "inativ_aviso_minutos")
    op.drop_column("whatsapp_settings", "inativ_encerramento_ativa")
