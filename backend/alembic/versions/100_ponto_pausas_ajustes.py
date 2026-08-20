"""Ponto v2: flag anulada para ajustes admin (#767).

Revision ID: 100_ponto_pausas_ajustes
Revises: 099_controle_ponto
Create Date: 2026-08-20
"""

import sqlalchemy as sa
from alembic import op

revision = "100_ponto_pausas_ajustes"
down_revision = "099_controle_ponto"
branch_labels = None
depends_on = None


def _colunas(insp, tabela: str) -> set[str]:
    if not insp.has_table(tabela):
        return set()
    return {c["name"] for c in insp.get_columns(tabela)}


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = _colunas(insp, "ponto_batidas")
    if "anulada" not in cols:
        op.add_column(
            "ponto_batidas",
            sa.Column("anulada", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = _colunas(insp, "ponto_batidas")
    if "anulada" in cols:
        op.drop_column("ponto_batidas", "anulada")
