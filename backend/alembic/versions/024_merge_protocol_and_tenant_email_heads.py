"""Unifica heads: ramo protocol_sequences (main) + ramo tenants/email.

Revision ID: 024_merge_protocol_tenant_heads
Revises: 018_protocol_sequences_yyyymm, 023_tenants
Create Date: 2026-05-15
"""

revision = "024_merge_protocol_tenant_heads"
down_revision = ("018_protocol_sequences_yyyymm", "023_tenants")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
