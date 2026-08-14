"""Registo de entrega pós-health ao contacto da licença.

Revision ID: 090_saas_entrega
Revises: 089_lead_licenca
Create Date: 2026-08-10
"""

import sqlalchemy as sa
from alembic import op

revision = "090_saas_entrega"
down_revision = "089_lead_licenca"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("clientes_saas"):
        return
    cols = {c["name"] for c in insp.get_columns("clientes_saas")}
    if "entrega_notificada_em" not in cols:
        op.add_column(
            "clientes_saas",
            sa.Column("entrega_notificada_em", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("clientes_saas"):
        return
    cols = {c["name"] for c in insp.get_columns("clientes_saas")}
    if "entrega_notificada_em" in cols:
        op.drop_column("clientes_saas", "entrega_notificada_em")
