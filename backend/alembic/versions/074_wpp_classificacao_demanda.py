"""WhatsApp: classificação de demanda pendente após inatividade.

Revision ID: 074_wpp_classificacao_demanda
Revises: 073_wpp_inatividade_pausa
Create Date: 2026-07-18
"""

import sqlalchemy as sa
from alembic import op

revision = "074_wpp_classificacao_demanda"
down_revision = "073_wpp_inatividade_pausa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("whatsapp_chats"):
        return
    cols = {c["name"] for c in insp.get_columns("whatsapp_chats")}
    if "classificacao_demanda_pendente" not in cols:
        op.add_column(
            "whatsapp_chats",
            sa.Column(
                "classificacao_demanda_pendente",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("whatsapp_chats"):
        return
    cols = {c["name"] for c in insp.get_columns("whatsapp_chats")}
    if "classificacao_demanda_pendente" in cols:
        op.drop_column("whatsapp_chats", "classificacao_demanda_pendente")
