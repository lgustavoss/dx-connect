"""SLA: natureza opcional nas políticas (#259 v2).

Revision ID: 051_sla_policy_natureza
Revises: 050_status_ticket_pausa_sla
Create Date: 2026-06-23
"""

import sqlalchemy as sa
from alembic import op

revision = "051_sla_policy_natureza"
down_revision = "050_status_ticket_pausa_sla"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_sla_policies_setor_prioridade", "sla_policies", type_="unique")
    op.add_column("sla_policies", sa.Column("natureza_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_sla_policies_natureza_id",
        "sla_policies",
        "ticket_naturezas",
        ["natureza_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_sla_policies_natureza_id"), "sla_policies", ["natureza_id"], unique=False)
    op.create_unique_constraint(
        "uq_sla_policies_setor_prioridade_natureza",
        "sla_policies",
        ["tenant_id", "setor_id", "prioridade", "natureza_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_sla_policies_setor_prioridade_natureza", "sla_policies", type_="unique")
    op.drop_index(op.f("ix_sla_policies_natureza_id"), table_name="sla_policies")
    op.drop_constraint("fk_sla_policies_natureza_id", "sla_policies", type_="foreignkey")
    op.drop_column("sla_policies", "natureza_id")
    op.create_unique_constraint(
        "uq_sla_policies_setor_prioridade",
        "sla_policies",
        ["tenant_id", "setor_id", "prioridade"],
    )
