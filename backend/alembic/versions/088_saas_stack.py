"""Estado da stack Docker por licença SaaS (suspender/reativar).

Revision ID: 088_saas_stack
Revises: 087_saas_aprovacao
Create Date: 2026-08-10
"""

import sqlalchemy as sa
from alembic import op

revision = "088_saas_stack"
down_revision = "087_saas_aprovacao"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("clientes_saas"):
        return
    cols = {c["name"] for c in insp.get_columns("clientes_saas")}
    if "stack_status" not in cols:
        op.add_column("clientes_saas", sa.Column("stack_status", sa.String(length=20), nullable=True))
    if "stack_ops_pendente" not in cols:
        op.add_column(
            "clientes_saas",
            sa.Column("stack_ops_pendente", sa.String(length=10), nullable=True),
        )
    if "stack_ops_mensagem" not in cols:
        op.add_column("clientes_saas", sa.Column("stack_ops_mensagem", sa.Text(), nullable=True))
    if "stack_ops_atualizado_em" not in cols:
        op.add_column(
            "clientes_saas",
            sa.Column("stack_ops_atualizado_em", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("clientes_saas"):
        return
    cols = {c["name"] for c in insp.get_columns("clientes_saas")}
    for col in ("stack_ops_atualizado_em", "stack_ops_mensagem", "stack_ops_pendente", "stack_status"):
        if col in cols:
            op.drop_column("clientes_saas", col)
