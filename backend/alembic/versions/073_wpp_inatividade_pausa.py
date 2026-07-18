"""WhatsApp: pausa do timer de inatividade no chat.

Revision ID: 073_wpp_inatividade_pausa
Revises: 072_chat_interno_silenciar
Create Date: 2026-07-18
"""

import sqlalchemy as sa
from alembic import op

revision = "073_wpp_inatividade_pausa"
down_revision = "072_chat_interno_silenciar"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("whatsapp_chats"):
        return
    cols = {c["name"] for c in insp.get_columns("whatsapp_chats")}
    if "inatividade_pausada" not in cols:
        op.add_column(
            "whatsapp_chats",
            sa.Column("inatividade_pausada", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    if "inatividade_retomada_em" not in cols:
        op.add_column(
            "whatsapp_chats",
            sa.Column("inatividade_retomada_em", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("whatsapp_chats"):
        return
    cols = {c["name"] for c in insp.get_columns("whatsapp_chats")}
    if "inatividade_retomada_em" in cols:
        op.drop_column("whatsapp_chats", "inatividade_retomada_em")
    if "inatividade_pausada" in cols:
        op.drop_column("whatsapp_chats", "inatividade_pausada")
