"""email_settings: janela antes de enviar resposta ao cliente (#140).

Revision ID: 028_email_ticket_grace
Revises: 027_ticket_msg_email_outbox
Create Date: 2026-05-21
"""

from alembic import op
import sqlalchemy as sa

revision = "028_email_ticket_grace"
down_revision = "027_ticket_msg_email_outbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "email_settings",
        sa.Column("ticket_mensagem_email_grace_seconds", sa.Integer(), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE email_settings SET ticket_mensagem_email_grace_seconds = 120 "
            "WHERE ticket_mensagem_email_grace_seconds IS NULL"
        )
    )


def downgrade() -> None:
    op.drop_column("email_settings", "ticket_mensagem_email_grace_seconds")
