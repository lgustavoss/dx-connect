"""Valor mensal negociado por licença SaaS.

Revision ID: 123_saas_preco_negociado
Revises: 122_saas_preco_modulos
Create Date: 2026-08-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "123_saas_preco_negociado"
down_revision = "122_saas_preco_modulos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("clientes_saas"):
        return
    cols = {c["name"] for c in insp.get_columns("clientes_saas")}
    if "preco_mensal_negociado" not in cols:
        op.add_column(
            "clientes_saas",
            sa.Column("preco_mensal_negociado", sa.Numeric(12, 2), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("clientes_saas"):
        return
    cols = {c["name"] for c in insp.get_columns("clientes_saas")}
    if "preco_mensal_negociado" in cols:
        op.drop_column("clientes_saas", "preco_mensal_negociado")
