"""Cache dos computadores do RustDesk auto-hospedado (#1184).

Revision ID: 149_rustdesk_peers
Revises: 148_chat_negociacao
Create Date: 2026-10-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "149_rustdesk_peers"
down_revision = "148_chat_negociacao"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rustdesk_peers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rustdesk_id", sa.String(length=253), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("sistema", sa.String(length=120), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_rustdesk_peers_rustdesk_id", "rustdesk_peers", ["rustdesk_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_rustdesk_peers_rustdesk_id", table_name="rustdesk_peers")
    op.drop_table("rustdesk_peers")
