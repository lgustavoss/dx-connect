"""email_inbound_received: idempotência por Message-ID (ingestão webhook).

Revision ID: 020_email_inbound
Revises: 019_empresa_endereco
Create Date: 2026-05-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "020_email_inbound"
down_revision = "019_empresa_endereco"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if insp.has_table("email_inbound_received"):
        return
    op.create_table(
        "email_inbound_received",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("message_id_normalized", sa.String(length=998), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("from_address", sa.String(length=512), nullable=True),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_email_inbound_received_message_id_normalized"),
        "email_inbound_received",
        ["message_id_normalized"],
        unique=True,
    )
    op.create_index(op.f("ix_email_inbound_received_ticket_id"), "email_inbound_received", ["ticket_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if not insp.has_table("email_inbound_received"):
        return
    op.drop_index(op.f("ix_email_inbound_received_ticket_id"), table_name="email_inbound_received")
    op.drop_index(op.f("ix_email_inbound_received_message_id_normalized"), table_name="email_inbound_received")
    op.drop_table("email_inbound_received")
