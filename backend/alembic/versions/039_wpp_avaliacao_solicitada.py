"""WhatsApp: flag avaliacao_solicitada no chat.

Revision ID: 039_wpp_avaliacao_solicitada
Revises: 038_wpp_avaliacao
Create Date: 2026-06-09
"""

from alembic import op
import sqlalchemy as sa

revision = "039_wpp_avaliacao_solicitada"
down_revision = "038_wpp_avaliacao"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "whatsapp_chats",
        sa.Column("avaliacao_solicitada", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("whatsapp_chats", "avaliacao_solicitada", server_default=None)


def downgrade() -> None:
    op.drop_column("whatsapp_chats", "avaliacao_solicitada")
