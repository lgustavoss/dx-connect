"""Aprovação go-live de licenças SaaS (control-plane).

Revision ID: 087_saas_aprovacao
Revises: 086_leads_comerciais
Create Date: 2026-08-10
"""

import sqlalchemy as sa
from alembic import op

revision = "087_saas_aprovacao"
down_revision = "086_leads_comerciais"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("clientes_saas"):
        return
    cols = {c["name"] for c in insp.get_columns("clientes_saas")}
    if "aprovacao_status" not in cols:
        op.add_column(
            "clientes_saas",
            sa.Column("aprovacao_status", sa.String(length=20), nullable=False, server_default="aprovado"),
        )
        op.alter_column("clientes_saas", "aprovacao_status", server_default=None)
    if "aprovacao_notas" not in cols:
        op.add_column("clientes_saas", sa.Column("aprovacao_notas", sa.Text(), nullable=True))
    if "aprovacao_em" not in cols:
        op.add_column(
            "clientes_saas",
            sa.Column("aprovacao_em", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("clientes_saas"):
        return
    cols = {c["name"] for c in insp.get_columns("clientes_saas")}
    for col in ("aprovacao_em", "aprovacao_notas", "aprovacao_status"):
        if col in cols:
            op.drop_column("clientes_saas", col)
