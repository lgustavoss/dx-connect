"""WhatsApp: editar e apagar para todos (#630 lote 3).

Revision ID: 080_wpp_edicao_apagar
Revises: 079_wpp_reacoes
Create Date: 2026-08-01
"""

import sqlalchemy as sa
from alembic import op

revision = "080_wpp_edicao_apagar"
down_revision = "079_wpp_reacoes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("whatsapp_mensagens"):
        return
    cols = {c["name"] for c in insp.get_columns("whatsapp_mensagens")}
    if "editada_em" not in cols:
        op.add_column(
            "whatsapp_mensagens",
            sa.Column("editada_em", sa.DateTime(timezone=True), nullable=True),
        )
    if "apagada_em" not in cols:
        op.add_column(
            "whatsapp_mensagens",
            sa.Column("apagada_em", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("whatsapp_mensagens"):
        return
    cols = {c["name"] for c in insp.get_columns("whatsapp_mensagens")}
    if "apagada_em" in cols:
        op.drop_column("whatsapp_mensagens", "apagada_em")
    if "editada_em" in cols:
        op.drop_column("whatsapp_mensagens", "editada_em")
