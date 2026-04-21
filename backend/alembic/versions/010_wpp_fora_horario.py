"""WhatsApp: mensagem automática fora do horário.

Revision ID: 010_wpp_fora_horario
Revises: 009_wpp_auto_msgs
Create Date: 2026-04-21
"""

from alembic import op
import sqlalchemy as sa


revision = "010_wpp_fora_horario"
down_revision = "009_wpp_auto_msgs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "whatsapp_settings",
        sa.Column("auto_msg_fora_horario_ativa", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column("whatsapp_settings", sa.Column("auto_msg_fora_horario_texto", sa.Text(), nullable=True))
    op.add_column("whatsapp_settings", sa.Column("horario_inicio", sa.String(length=5), nullable=True))
    op.add_column("whatsapp_settings", sa.Column("horario_fim", sa.String(length=5), nullable=True))
    op.add_column(
        "whatsapp_settings",
        sa.Column("horario_timezone", sa.String(length=64), nullable=False, server_default="America/Sao_Paulo"),
    )
    op.alter_column("whatsapp_settings", "auto_msg_fora_horario_ativa", server_default=None)
    op.alter_column("whatsapp_settings", "horario_timezone", server_default=None)


def downgrade() -> None:
    op.drop_column("whatsapp_settings", "horario_timezone")
    op.drop_column("whatsapp_settings", "horario_fim")
    op.drop_column("whatsapp_settings", "horario_inicio")
    op.drop_column("whatsapp_settings", "auto_msg_fora_horario_texto")
    op.drop_column("whatsapp_settings", "auto_msg_fora_horario_ativa")

