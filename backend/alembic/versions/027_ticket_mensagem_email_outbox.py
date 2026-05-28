"""ticket_mensagens: fila de envio de e-mail com janela de edição (#140).

Revision ID: 027_ticket_msg_email_outbox
Revises: 026_ticket_msg_autor_ext
Create Date: 2026-05-21
"""

from alembic import op
import sqlalchemy as sa

revision = "027_ticket_msg_email_outbox"
down_revision = "026_ticket_msg_autor_ext"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ticket_mensagens", sa.Column("email_status", sa.String(length=32), nullable=True))
    op.add_column("ticket_mensagens", sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ticket_mensagens", sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "ticket_mensagens",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("ticket_mensagens", sa.Column("edit_lock_token", sa.String(length=64), nullable=True))
    op.add_column(
        "ticket_mensagens",
        sa.Column("edit_lock_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_ticket_mensagens_email_status_scheduled",
        "ticket_mensagens",
        ["email_status", "scheduled_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ticket_mensagens_email_status_scheduled", table_name="ticket_mensagens")
    op.drop_column("ticket_mensagens", "edit_lock_expires_at")
    op.drop_column("ticket_mensagens", "edit_lock_token")
    op.drop_column("ticket_mensagens", "updated_at")
    op.drop_column("ticket_mensagens", "sent_at")
    op.drop_column("ticket_mensagens", "scheduled_at")
    op.drop_column("ticket_mensagens", "email_status")
