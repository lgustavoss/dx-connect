"""Preço/limites nos planos + snapshot de módulos na licença.

Revision ID: 092_saas_licenca_completa
Revises: 091_saas_planos
Create Date: 2026-08-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "092_saas_licenca_completa"
down_revision = "091_saas_planos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("saas_planos"):
        cols = {c["name"] for c in insp.get_columns("saas_planos")}
        if "preco_mensal" not in cols:
            op.add_column(
                "saas_planos",
                sa.Column("preco_mensal", sa.Numeric(12, 2), nullable=True),
            )
        if "max_postos" not in cols:
            op.add_column("saas_planos", sa.Column("max_postos", sa.Integer(), nullable=True))
        if "max_usuarios" not in cols:
            op.add_column("saas_planos", sa.Column("max_usuarios", sa.Integer(), nullable=True))

    if insp.has_table("clientes_saas"):
        cols = {c["name"] for c in insp.get_columns("clientes_saas")}
        if "modulos_snapshot" not in cols:
            op.add_column("clientes_saas", sa.Column("modulos_snapshot", sa.JSON(), nullable=True))
        if "max_postos" not in cols:
            op.add_column("clientes_saas", sa.Column("max_postos", sa.Integer(), nullable=True))
        if "max_usuarios" not in cols:
            op.add_column("clientes_saas", sa.Column("max_usuarios", sa.Integer(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("clientes_saas"):
        cols = {c["name"] for c in insp.get_columns("clientes_saas")}
        for c in ("max_usuarios", "max_postos", "modulos_snapshot"):
            if c in cols:
                op.drop_column("clientes_saas", c)
    if insp.has_table("saas_planos"):
        cols = {c["name"] for c in insp.get_columns("saas_planos")}
        for c in ("max_usuarios", "max_postos", "preco_mensal"):
            if c in cols:
                op.drop_column("saas_planos", c)
