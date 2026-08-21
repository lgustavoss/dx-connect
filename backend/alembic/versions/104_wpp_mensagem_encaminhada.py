"""WhatsApp: flag de mensagem encaminhada (#827).

Revision ID: 104_wpp_mensagem_encaminhada
Revises: 103_implantacao_checklist
Create Date: 2026-08-21
"""

import sqlalchemy as sa
from alembic import op

revision = "104_wpp_mensagem_encaminhada"
down_revision = "103_implantacao_checklist"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("whatsapp_mensagens"):
        return
    cols = {c["name"] for c in insp.get_columns("whatsapp_mensagens")}
    if "is_forwarded" not in cols:
        op.add_column(
            "whatsapp_mensagens",
            sa.Column("is_forwarded", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )
    if "forwarding_score" not in cols:
        op.add_column(
            "whatsapp_mensagens",
            sa.Column("forwarding_score", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("whatsapp_mensagens"):
        return
    cols = {c["name"] for c in insp.get_columns("whatsapp_mensagens")}
    if "forwarding_score" in cols:
        op.drop_column("whatsapp_mensagens", "forwarding_score")
    if "is_forwarded" in cols:
        op.drop_column("whatsapp_mensagens", "is_forwarded")
