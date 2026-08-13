"""Catálogo comercial: flag aplica_tier_posto nos itens (#332).

Revision ID: 083_comercial_custos_tier_posto
Revises: 082_comercial_catalogo_custos
Create Date: 2026-08-08
"""

import sqlalchemy as sa
from alembic import op

revision = "083_comercial_custos_tier_posto"
down_revision = "082_comercial_catalogo_custos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("custo_catalogo_itens"):
        return
    cols = {c["name"] for c in insp.get_columns("custo_catalogo_itens")}
    if "aplica_tier_posto" not in cols:
        op.add_column(
            "custo_catalogo_itens",
            sa.Column(
                "aplica_tier_posto",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("custo_catalogo_itens"):
        return
    cols = {c["name"] for c in insp.get_columns("custo_catalogo_itens")}
    if "aplica_tier_posto" in cols:
        op.drop_column("custo_catalogo_itens", "aplica_tier_posto")
