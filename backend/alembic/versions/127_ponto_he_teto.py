"""HE antecipada + teto por atendente (#966).

Revision ID: 127_ponto_he_teto
Revises: 126_ponto_hora_extra
Create Date: 2026-08-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "127_ponto_he_teto"
down_revision = "126_ponto_hora_extra"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("atendentes"):
        cols = {c["name"] for c in insp.get_columns("atendentes")}
        if "he_teto_minutos" not in cols:
            op.add_column(
                "atendentes",
                sa.Column("he_teto_minutos", sa.Integer(), nullable=True),
            )

    if insp.has_table("ponto_hora_extra"):
        cols = {c["name"] for c in insp.get_columns("ponto_hora_extra")}
        if "origem" not in cols:
            op.add_column(
                "ponto_hora_extra",
                sa.Column("origem", sa.String(20), nullable=False, server_default="solicitacao"),
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("ponto_hora_extra"):
        cols = {c["name"] for c in insp.get_columns("ponto_hora_extra")}
        if "origem" in cols:
            op.drop_column("ponto_hora_extra", "origem")
    if insp.has_table("atendentes"):
        cols = {c["name"] for c in insp.get_columns("atendentes")}
        if "he_teto_minutos" in cols:
            op.drop_column("atendentes", "he_teto_minutos")
