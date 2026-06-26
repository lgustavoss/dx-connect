"""Status de ticket: flag pausa_sla para congelar contagem SLA (#418).

Revision ID: 050_status_ticket_pausa_sla
Revises: 049_whatsapp_chat_demandas
Create Date: 2026-06-23
"""

import sqlalchemy as sa
from alembic import op

revision = "050_status_ticket_pausa_sla"
down_revision = "049_whatsapp_chat_demandas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "status_ticket",
        sa.Column("pausa_sla", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.execute(
        sa.text("UPDATE status_ticket SET pausa_sla = true WHERE slug = 'aguardando_cliente'")
    )


def downgrade() -> None:
    op.drop_column("status_ticket", "pausa_sla")
