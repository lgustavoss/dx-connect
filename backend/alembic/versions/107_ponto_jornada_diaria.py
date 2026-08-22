"""Ponto: jornada diária (minutos) para calendário (#842).

Revision ID: 107_ponto_jornada_diaria
Revises: 106_faturamento_fatura
Create Date: 2026-08-21
"""

import sqlalchemy as sa
from alembic import op

revision = "107_ponto_jornada_diaria"
down_revision = "106_faturamento_fatura"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("ponto_settings"):
        return
    cols = {c["name"] for c in insp.get_columns("ponto_settings")}
    if "jornada_diaria_minutos" not in cols:
        op.add_column(
            "ponto_settings",
            sa.Column("jornada_diaria_minutos", sa.Integer(), nullable=False, server_default="480"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("ponto_settings"):
        return
    cols = {c["name"] for c in insp.get_columns("ponto_settings")}
    if "jornada_diaria_minutos" in cols:
        op.drop_column("ponto_settings", "jornada_diaria_minutos")
