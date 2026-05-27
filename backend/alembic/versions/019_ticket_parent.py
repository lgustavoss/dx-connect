"""tickets: vínculo opcional ticket pai (parent_ticket_id).

Revision ID: 019_ticket_parent
Revises: 018_protocol_sequences_yyyymm
Create Date: 2026-05-13
"""

from alembic import op
import sqlalchemy as sa


revision = "019_ticket_parent"
down_revision = "018_protocol_sequences_yyyymm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tickets",
        sa.Column("parent_ticket_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_tickets_parent_ticket_id", "tickets", ["parent_ticket_id"], unique=False)
    op.create_foreign_key(
        "fk_tickets_parent_ticket_id_tickets",
        "tickets",
        "tickets",
        ["parent_ticket_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_tickets_parent_ticket_id_tickets", "tickets", type_="foreignkey")
    op.drop_index("ix_tickets_parent_ticket_id", table_name="tickets")
    op.drop_column("tickets", "parent_ticket_id")
