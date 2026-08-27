"""Teto mensal de HE (#974).

Revision ID: 130_ponto_he_teto_mensal
Revises: 129_merge_he_teto_versao
Create Date: 2026-08-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "130_ponto_he_teto_mensal"
down_revision = "129_merge_he_teto_versao"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("ponto_settings"):
        cols = {c["name"] for c in insp.get_columns("ponto_settings")}
        if "he_teto_mensal_minutos" not in cols:
            op.add_column(
                "ponto_settings",
                sa.Column("he_teto_mensal_minutos", sa.Integer(), nullable=True),
            )

    if insp.has_table("atendentes"):
        cols = {c["name"] for c in insp.get_columns("atendentes")}
        if "he_teto_mensal_minutos" not in cols:
            op.add_column(
                "atendentes",
                sa.Column("he_teto_mensal_minutos", sa.Integer(), nullable=True),
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("atendentes"):
        cols = {c["name"] for c in insp.get_columns("atendentes")}
        if "he_teto_mensal_minutos" in cols:
            op.drop_column("atendentes", "he_teto_mensal_minutos")
    if insp.has_table("ponto_settings"):
        cols = {c["name"] for c in insp.get_columns("ponto_settings")}
        if "he_teto_mensal_minutos" in cols:
            op.drop_column("ponto_settings", "he_teto_mensal_minutos")
