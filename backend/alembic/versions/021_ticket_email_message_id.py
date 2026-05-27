"""Índice Message-ID → ticket (threading e-mail ↔ ticket).

Revision ID: 021_ticket_email_mid
Revises: 020_email_inbound
Create Date: 2026-05-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


revision = "021_ticket_email_mid"
down_revision = "020_email_inbound"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if insp.has_table("ticket_email_message_id"):
        return
    op.create_table(
        "ticket_email_message_id",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("message_id_normalized", sa.String(length=998), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ticket_email_message_id_message_id_normalized"),
        "ticket_email_message_id",
        ["message_id_normalized"],
        unique=True,
    )
    op.create_index(
        op.f("ix_ticket_email_message_id_ticket_id"),
        "ticket_email_message_id",
        ["ticket_id"],
        unique=False,
    )
    if insp.has_table("email_inbound_received"):
        bind.execute(
            text(
                """
                INSERT INTO ticket_email_message_id (message_id_normalized, ticket_id, source)
                SELECT message_id_normalized, ticket_id, 'inbound'
                FROM email_inbound_received
                WHERE NOT EXISTS (
                    SELECT 1 FROM ticket_email_message_id t
                    WHERE t.message_id_normalized = email_inbound_received.message_id_normalized
                )
                """
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if not insp.has_table("ticket_email_message_id"):
        return
    op.drop_index(op.f("ix_ticket_email_message_id_ticket_id"), table_name="ticket_email_message_id")
    op.drop_index(op.f("ix_ticket_email_message_id_message_id_normalized"), table_name="ticket_email_message_id")
    op.drop_table("ticket_email_message_id")
