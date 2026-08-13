"""Vínculo lead comercial → licença SaaS.

Revision ID: 089_lead_licenca
Revises: 088_saas_stack
Create Date: 2026-08-10
"""

import sqlalchemy as sa
from alembic import op

revision = "089_lead_licenca"
down_revision = "088_saas_stack"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("leads_comerciais"):
        cols = {c["name"] for c in insp.get_columns("leads_comerciais")}
        if "cliente_saas_id" not in cols:
            op.add_column(
                "leads_comerciais",
                sa.Column("cliente_saas_id", sa.Integer(), nullable=True),
            )
            op.create_index("ix_leads_comerciais_cliente_saas_id", "leads_comerciais", ["cliente_saas_id"])
            op.create_foreign_key(
                "fk_leads_comerciais_cliente_saas",
                "leads_comerciais",
                "clientes_saas",
                ["cliente_saas_id"],
                ["id"],
                ondelete="SET NULL",
            )
    if insp.has_table("clientes_saas"):
        cols = {c["name"] for c in insp.get_columns("clientes_saas")}
        if "lead_comercial_id" not in cols:
            op.add_column(
                "clientes_saas",
                sa.Column("lead_comercial_id", sa.Integer(), nullable=True),
            )
            op.create_index("ix_clientes_saas_lead_comercial_id", "clientes_saas", ["lead_comercial_id"])
            op.create_foreign_key(
                "fk_clientes_saas_lead_comercial",
                "clientes_saas",
                "leads_comerciais",
                ["lead_comercial_id"],
                ["id"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("clientes_saas"):
        cols = {c["name"] for c in insp.get_columns("clientes_saas")}
        if "lead_comercial_id" in cols:
            op.drop_constraint("fk_clientes_saas_lead_comercial", "clientes_saas", type_="foreignkey")
            op.drop_index("ix_clientes_saas_lead_comercial_id", table_name="clientes_saas")
            op.drop_column("clientes_saas", "lead_comercial_id")
    if insp.has_table("leads_comerciais"):
        cols = {c["name"] for c in insp.get_columns("leads_comerciais")}
        if "cliente_saas_id" in cols:
            op.drop_constraint("fk_leads_comerciais_cliente_saas", "leads_comerciais", type_="foreignkey")
            op.drop_index("ix_leads_comerciais_cliente_saas_id", table_name="leads_comerciais")
            op.drop_column("leads_comerciais", "cliente_saas_id")
