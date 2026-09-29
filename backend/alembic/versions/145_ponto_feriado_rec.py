"""Feriado da instância com recorrência anual.

Revision ID: 145_ponto_feriado_rec
Revises: 144_ponto_solic_ant
Create Date: 2026-09-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "145_ponto_feriado_rec"
down_revision = "144_ponto_solic_ant"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("ponto_feriados"):
        return
    cols = {c["name"] for c in insp.get_columns("ponto_feriados")}
    if "recorrente_anual" not in cols:
        op.add_column(
            "ponto_feriados",
            sa.Column(
                "recorrente_anual",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("ponto_feriados"):
        return
    cols = {c["name"] for c in insp.get_columns("ponto_feriados")}
    if "recorrente_anual" in cols:
        op.drop_column("ponto_feriados", "recorrente_anual")
