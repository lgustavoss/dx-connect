"""WhatsApp: citação (reply) em mensagens.

Revision ID: 015_wpp_citacao
Revises: 014_wpp_reads
Create Date: 2026-04-21
"""

from alembic import op
import sqlalchemy as sa


revision = "015_wpp_citacao"
down_revision = "014_wpp_reads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = [c["name"] for c in insp.get_columns("whatsapp_mensagens")] if insp.has_table("whatsapp_mensagens") else []
    if "quoted_wa_message_id" not in cols:
        op.add_column(
            "whatsapp_mensagens",
            sa.Column("quoted_wa_message_id", sa.String(length=128), nullable=True),
        )
    if "quoted_corpo_preview" not in cols:
        op.add_column(
            "whatsapp_mensagens",
            sa.Column("quoted_corpo_preview", sa.String(length=500), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("whatsapp_mensagens"):
        return
    cols = [c["name"] for c in insp.get_columns("whatsapp_mensagens")]
    if "quoted_corpo_preview" in cols:
        op.drop_column("whatsapp_mensagens", "quoted_corpo_preview")
    if "quoted_wa_message_id" in cols:
        op.drop_column("whatsapp_mensagens", "quoted_wa_message_id")
