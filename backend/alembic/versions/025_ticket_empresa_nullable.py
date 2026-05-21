"""tickets: empresa_id opcional (triagem após ingestão por e-mail).

Revision ID: 025_ticket_empresa_null
Revises: 024_merge_protocol_tenant_heads
Create Date: 2026-05-17
"""

from alembic import op
import sqlalchemy as sa

revision = "025_ticket_empresa_null"
down_revision = "024_merge_protocol_tenant_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("tickets", "empresa_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    op.alter_column("tickets", "empresa_id", existing_type=sa.Integer(), nullable=False)
