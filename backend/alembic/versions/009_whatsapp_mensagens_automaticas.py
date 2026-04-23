"""WhatsApp: mensagens automáticas + templates em settings.

Revision ID: 009_wpp_auto_msgs
Revises: 008_whatsapp_mensagem_midia
Create Date: 2026-04-21
"""

from alembic import op
import sqlalchemy as sa


revision = "009_wpp_auto_msgs"
down_revision = "008_whatsapp_mensagem_midia"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "whatsapp_settings",
        sa.Column("auto_msg_espera_ativa", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column("whatsapp_settings", sa.Column("auto_msg_espera_texto", sa.Text(), nullable=True))
    op.add_column(
        "whatsapp_settings",
        sa.Column("auto_msg_assumido_ativa", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column("whatsapp_settings", sa.Column("auto_msg_assumido_texto", sa.Text(), nullable=True))
    op.add_column(
        "whatsapp_settings",
        sa.Column("auto_msg_encerrado_ativa", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column("whatsapp_settings", sa.Column("auto_msg_encerrado_texto", sa.Text(), nullable=True))
    op.alter_column("whatsapp_settings", "auto_msg_espera_ativa", server_default=None)
    op.alter_column("whatsapp_settings", "auto_msg_assumido_ativa", server_default=None)
    op.alter_column("whatsapp_settings", "auto_msg_encerrado_ativa", server_default=None)

    op.add_column("whatsapp_mensagens", sa.Column("evento_sistema", sa.String(length=40), nullable=True))
    op.create_index(op.f("ix_whatsapp_mensagens_evento_sistema"), "whatsapp_mensagens", ["evento_sistema"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_whatsapp_mensagens_evento_sistema"), table_name="whatsapp_mensagens")
    op.drop_column("whatsapp_mensagens", "evento_sistema")
    op.drop_column("whatsapp_settings", "auto_msg_encerrado_texto")
    op.drop_column("whatsapp_settings", "auto_msg_encerrado_ativa")
    op.drop_column("whatsapp_settings", "auto_msg_assumido_texto")
    op.drop_column("whatsapp_settings", "auto_msg_assumido_ativa")
    op.drop_column("whatsapp_settings", "auto_msg_espera_texto")
    op.drop_column("whatsapp_settings", "auto_msg_espera_ativa")

