"""Unifica heads: tickets pai/filho + outbox de e-mail (grace).

Revision ID: 029_merge_ticket_parent_outbox
Revises: 019_ticket_parent, 028_email_ticket_grace
Create Date: 2026-05-28
"""

revision = "029_merge_ticket_parent_outbox"
down_revision = ("019_ticket_parent", "028_email_ticket_grace")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
