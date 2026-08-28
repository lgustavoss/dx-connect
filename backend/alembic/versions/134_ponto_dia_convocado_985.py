"""Lote H: dia convocado (#985).

Revision ID: 134_ponto_dia_convocado_985
Revises: 133_ponto_lote_e
Create Date: 2026-08-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "134_ponto_dia_convocado_985"
down_revision = "133_ponto_lote_e"
branch_labels = None
depends_on = None

_TABLE = "ponto_dias_convocados"

_INDEXES: tuple[tuple[str, list[str]], ...] = (
    ("ix_ponto_dias_convocados_tenant_id", ["tenant_id"]),
    ("ix_ponto_dias_convocados_atendente_id", ["atendente_id"]),
    ("ix_ponto_dias_convocados_data_ref", ["data_ref"]),
    ("ix_ponto_dias_convocados_atendente_data", ["atendente_id", "data_ref"]),
)


def _ensure_indexes(insp: sa.Inspector) -> None:
    if not insp.has_table(_TABLE):
        return
    idxs = {i["name"] for i in insp.get_indexes(_TABLE)}
    for name, columns in _INDEXES:
        if name not in idxs:
            op.create_index(name, _TABLE, columns)


def _ensure_columns(insp: sa.Inspector) -> None:
    """Colunas opcionais/ausentes em DDL manual parcial."""
    if not insp.has_table(_TABLE):
        return
    cols = {c["name"] for c in insp.get_columns(_TABLE)}
    if "tolerancia_minutos" not in cols:
        op.add_column(_TABLE, sa.Column("tolerancia_minutos", sa.Integer(), nullable=True))
    if "estado" not in cols:
        op.add_column(
            _TABLE,
            sa.Column("estado", sa.String(20), nullable=False, server_default="ativa"),
        )
    if "criado_por_id" not in cols:
        op.add_column(
            _TABLE,
            sa.Column(
                "criado_por_id",
                sa.Integer(),
                sa.ForeignKey("atendentes.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
    if "created_at" not in cols:
        op.add_column(
            _TABLE,
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        )
    if "cancelado_por_id" not in cols:
        op.add_column(
            _TABLE,
            sa.Column(
                "cancelado_por_id",
                sa.Integer(),
                sa.ForeignKey("atendentes.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
    if "cancelado_em" not in cols:
        op.add_column(_TABLE, sa.Column("cancelado_em", sa.DateTime(timezone=True), nullable=True))


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table(_TABLE):
        op.create_table(
            _TABLE,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "tenant_id",
                sa.Integer(),
                sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column(
                "atendente_id",
                sa.Integer(),
                sa.ForeignKey("atendentes.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("data_ref", sa.Date(), nullable=False),
            sa.Column("inicio", sa.String(5), nullable=False),
            sa.Column("fim", sa.String(5), nullable=False),
            sa.Column("tolerancia_minutos", sa.Integer(), nullable=True),
            sa.Column("motivo", sa.String(1000), nullable=False),
            sa.Column("estado", sa.String(20), nullable=False, server_default="ativa"),
            sa.Column(
                "criado_por_id",
                sa.Integer(),
                sa.ForeignKey("atendentes.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column(
                "cancelado_por_id",
                sa.Integer(),
                sa.ForeignKey("atendentes.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("cancelado_em", sa.DateTime(timezone=True), nullable=True),
        )
        for name, columns in _INDEXES:
            op.create_index(name, _TABLE, columns)
    else:
        _ensure_columns(insp)
        _ensure_indexes(insp)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table(_TABLE):
        op.drop_table(_TABLE)
