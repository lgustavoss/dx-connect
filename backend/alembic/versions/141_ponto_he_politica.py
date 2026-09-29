"""Política banco vs pagamento de HE (#1138).

Revision ID: 141_ponto_he_politica
Revises: 140_ponto_solic_ajuste_1135
Create Date: 2026-09-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "141_ponto_he_politica"
down_revision = "140_ponto_solic_ajuste_1135"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("ponto_settings"):
        return
    cols = {c["name"] for c in insp.get_columns("ponto_settings")}
    if "banco_horas_ativo" not in cols:
        op.add_column(
            "ponto_settings",
            sa.Column(
                "banco_horas_ativo",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
        )
    if "he_destino_excedente" not in cols:
        op.add_column(
            "ponto_settings",
            sa.Column(
                "he_destino_excedente",
                sa.String(20),
                nullable=False,
                server_default="banco",
            ),
        )
    if "he_banco_primeiros_minutos" not in cols:
        op.add_column(
            "ponto_settings",
            sa.Column(
                "he_banco_primeiros_minutos",
                sa.Integer(),
                nullable=False,
                server_default="120",
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("ponto_settings"):
        return
    cols = {c["name"] for c in insp.get_columns("ponto_settings")}
    for name in ("he_banco_primeiros_minutos", "he_destino_excedente", "banco_horas_ativo"):
        if name in cols:
            op.drop_column("ponto_settings", name)
