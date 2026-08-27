"""Locais de ponto por atendente + pin da empresa (#984).

Revision ID: 125_ponto_locais_atendente
Revises: 124_ponto_modo_jornada
Create Date: 2026-08-26
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "125_ponto_locais_atendente"
down_revision = "124_ponto_modo_jornada"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("empresa_sistema"):
        cols = {c["name"] for c in insp.get_columns("empresa_sistema")}
        if "latitude" not in cols:
            op.add_column("empresa_sistema", sa.Column("latitude", sa.Float(), nullable=True))
        if "longitude" not in cols:
            op.add_column("empresa_sistema", sa.Column("longitude", sa.Float(), nullable=True))
        if "ponto_raio_metros" not in cols:
            op.add_column(
                "empresa_sistema",
                sa.Column("ponto_raio_metros", sa.Integer(), nullable=False, server_default="200"),
            )

    if insp.has_table("atendentes"):
        cols = {c["name"] for c in insp.get_columns("atendentes")}
        if "usar_local_empresa" not in cols:
            op.add_column(
                "atendentes",
                sa.Column("usar_local_empresa", sa.Boolean(), nullable=False, server_default="true"),
            )
        if "local_empresa_raio_metros" not in cols:
            op.add_column(
                "atendentes",
                sa.Column("local_empresa_raio_metros", sa.Integer(), nullable=True),
            )

    if insp.has_table("ponto_locais"):
        cols = {c["name"] for c in insp.get_columns("ponto_locais")}
        if "atendente_id" not in cols:
            op.add_column(
                "ponto_locais",
                sa.Column(
                    "atendente_id",
                    sa.Integer(),
                    sa.ForeignKey("atendentes.id", ondelete="CASCADE"),
                    nullable=True,
                ),
            )
            op.create_index("ix_ponto_locais_atendente_id", "ponto_locais", ["atendente_id"])
        if "endereco" not in cols:
            op.add_column("ponto_locais", sa.Column("endereco", sa.String(512), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("ponto_locais"):
        cols = {c["name"] for c in insp.get_columns("ponto_locais")}
        if "endereco" in cols:
            op.drop_column("ponto_locais", "endereco")
        if "atendente_id" in cols:
            op.drop_index("ix_ponto_locais_atendente_id", table_name="ponto_locais")
            op.drop_column("ponto_locais", "atendente_id")

    if insp.has_table("atendentes"):
        cols = {c["name"] for c in insp.get_columns("atendentes")}
        for name in ("local_empresa_raio_metros", "usar_local_empresa"):
            if name in cols:
                op.drop_column("atendentes", name)

    if insp.has_table("empresa_sistema"):
        cols = {c["name"] for c in insp.get_columns("empresa_sistema")}
        for name in ("ponto_raio_metros", "longitude", "latitude"):
            if name in cols:
                op.drop_column("empresa_sistema", name)
