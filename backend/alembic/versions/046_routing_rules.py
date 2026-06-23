"""Tabela routing_rules (#258).

Revision ID: 046_routing_rules
Revises: 045_merge_setor_webhook
Create Date: 2026-06-17
"""

import sqlalchemy as sa
from alembic import op

revision = "046_routing_rules"
down_revision = "045_merge_setor_webhook"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "routing_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("rede_id", sa.Integer(), nullable=True),
        sa.Column("condicoes", sa.JSON(), nullable=False),
        sa.Column("acoes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["rede_id"], ["redes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_routing_rules_id"), "routing_rules", ["id"], unique=False)
    op.create_index(op.f("ix_routing_rules_tenant_id"), "routing_rules", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_routing_rules_rede_id"), "routing_rules", ["rede_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_routing_rules_rede_id"), table_name="routing_rules")
    op.drop_index(op.f("ix_routing_rules_tenant_id"), table_name="routing_rules")
    op.drop_index(op.f("ix_routing_rules_id"), table_name="routing_rules")
    op.drop_table("routing_rules")
