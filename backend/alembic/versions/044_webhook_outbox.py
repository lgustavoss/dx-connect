"""Fila de webhooks de saída (ticket fechado, etc.) (#119).

Revision ID: 044_webhook_outbox
Revises: 043_ticket_msg_email_retry
Create Date: 2026-06-12
"""

from alembic import op
import sqlalchemy as sa

revision = "044_webhook_outbox"
down_revision = "043_ticket_msg_email_retry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "webhook_outbox",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("dedup_key", sa.String(length=255), nullable=False),
        sa.Column("target_url", sa.String(length=2048), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pendente"),
        sa.Column("tentativas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_webhook_outbox_dedup_key", "webhook_outbox", ["dedup_key"], unique=False)
    op.create_index(
        "ix_webhook_outbox_status_scheduled",
        "webhook_outbox",
        ["status", "scheduled_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_webhook_outbox_status_scheduled", table_name="webhook_outbox")
    op.drop_index("ix_webhook_outbox_dedup_key", table_name="webhook_outbox")
    op.drop_table("webhook_outbox")
