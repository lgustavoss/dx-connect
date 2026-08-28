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


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("ponto_dias_convocados"):
        return
    op.create_table(
        "ponto_dias_convocados",
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
    op.create_index("ix_ponto_dias_convocados_tenant_id", "ponto_dias_convocados", ["tenant_id"])
    op.create_index("ix_ponto_dias_convocados_atendente_id", "ponto_dias_convocados", ["atendente_id"])
    op.create_index("ix_ponto_dias_convocados_data_ref", "ponto_dias_convocados", ["data_ref"])
    op.create_index(
        "ix_ponto_dias_convocados_atendente_data",
        "ponto_dias_convocados",
        ["atendente_id", "data_ref"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("ponto_dias_convocados"):
        op.drop_table("ponto_dias_convocados")
