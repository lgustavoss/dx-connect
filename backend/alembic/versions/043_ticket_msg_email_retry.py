"""ticket_mensagens: tentativas e último erro na fila de e-mail (#119).

Revision ID: 043_ticket_msg_email_retry
Revises: 042_atendente_notificacao
Create Date: 2026-06-12
"""

from alembic import op
import sqlalchemy as sa

revision = "043_ticket_msg_email_retry"
down_revision = "042_atendente_notificacao"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ticket_mensagens",
        sa.Column("email_send_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("ticket_mensagens", sa.Column("email_last_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("ticket_mensagens", "email_last_error")
    op.drop_column("ticket_mensagens", "email_send_attempts")
