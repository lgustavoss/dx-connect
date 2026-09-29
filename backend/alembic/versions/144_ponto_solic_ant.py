"""Snapshot do horário anterior em correção de ponto.

Revision ID: 144_ponto_solic_ant
Revises: 143_ponto_solic_anexo
Create Date: 2026-09-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "144_ponto_solic_ant"
down_revision = "143_ponto_solic_anexo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("ponto_solicitacoes_ajuste"):
        return
    cols = {c["name"] for c in insp.get_columns("ponto_solicitacoes_ajuste")}
    if "horario_anterior" not in cols:
        op.add_column(
            "ponto_solicitacoes_ajuste",
            sa.Column("horario_anterior", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("ponto_solicitacoes_ajuste"):
        return
    cols = {c["name"] for c in insp.get_columns("ponto_solicitacoes_ajuste")}
    if "horario_anterior" in cols:
        op.drop_column("ponto_solicitacoes_ajuste", "horario_anterior")
