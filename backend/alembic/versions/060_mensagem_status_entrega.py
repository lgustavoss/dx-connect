"""WhatsApp: status de entrega/leitura nas mensagens outbound.

Revision ID: 060_mensagem_status
Revises: 059_chat_interno_midia
Create Date: 2026-07-11
"""

import sqlalchemy as sa
from alembic import op

revision = "060_mensagem_status"
down_revision = "059_chat_interno_midia"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "whatsapp_mensagens",
        sa.Column("status_entrega", sa.String(length=20), nullable=True),
    )
    op.execute(
        """
        UPDATE whatsapp_mensagens
        SET status_entrega = 'enviada'
        WHERE direcao = 'outbound'
          AND wa_message_id IS NOT NULL
          AND (evento_sistema IS NULL OR evento_sistema = '')
        """
    )
    op.execute(
        """
        UPDATE whatsapp_mensagens
        SET status_entrega = 'pendente'
        WHERE direcao = 'outbound'
          AND wa_message_id IS NULL
          AND (evento_sistema IS NULL OR evento_sistema = '')
          AND status_entrega IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("whatsapp_mensagens", "status_entrega")
