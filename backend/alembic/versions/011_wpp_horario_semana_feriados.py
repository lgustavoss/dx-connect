"""WhatsApp: horário por dia da semana + feriados nacionais.

Revision ID: 011_wpp_horarios
Revises: 010_wpp_fora_horario
Create Date: 2026-04-21
"""

from alembic import op
import sqlalchemy as sa


revision = "011_wpp_horarios"
down_revision = "010_wpp_fora_horario"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("whatsapp_settings", sa.Column("horario_semana_json", sa.Text(), nullable=True))
    op.add_column(
        "whatsapp_settings",
        sa.Column("usar_feriados_nacionais", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.alter_column("whatsapp_settings", "usar_feriados_nacionais", server_default=None)


def downgrade() -> None:
    op.drop_column("whatsapp_settings", "usar_feriados_nacionais")
    op.drop_column("whatsapp_settings", "horario_semana_json")

