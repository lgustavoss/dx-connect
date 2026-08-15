"""WhatsApp: midia_nome_original nas mensagens (#679).

Revision ID: 094_wpp_midia_nome_original
Revises: 093_crm_leads_negociacao
Create Date: 2026-08-14
"""

import sqlalchemy as sa
from alembic import op

revision = "094_wpp_midia_nome_original"
down_revision = "093_crm_leads_negociacao"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("whatsapp_mensagens")}
    if "midia_nome_original" not in cols:
        op.add_column(
            "whatsapp_mensagens",
            sa.Column("midia_nome_original", sa.String(length=255), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("whatsapp_mensagens")}
    if "midia_nome_original" in cols:
        op.drop_column("whatsapp_mensagens", "midia_nome_original")
