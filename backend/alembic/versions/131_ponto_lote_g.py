"""Lote G: competência mensal e ciência do espelho (#978 / #979).

Revision ID: 131_ponto_lote_g
Revises: 130_ponto_lote_f
Create Date: 2026-08-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "131_ponto_lote_g"
down_revision = "130_ponto_lote_f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("ponto_competencias"):
        op.create_table(
            "ponto_competencias",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "tenant_id",
                sa.Integer(),
                sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("ano", sa.Integer(), nullable=False),
            sa.Column("mes", sa.Integer(), nullable=False),
            sa.Column("fechada", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("fechado_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "fechado_por_id",
                sa.Integer(),
                sa.ForeignKey("atendentes.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("reaberto_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "reaberto_por_id",
                sa.Integer(),
                sa.ForeignKey("atendentes.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("reabrir_motivo", sa.String(1000), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.UniqueConstraint("tenant_id", "ano", "mes", name="uq_ponto_competencias_tenant_ano_mes"),
        )
        op.create_index("ix_ponto_competencias_tenant_id", "ponto_competencias", ["tenant_id"])

    if not insp.has_table("ponto_espelho_ciencias"):
        op.create_table(
            "ponto_espelho_ciencias",
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
            sa.Column("ano", sa.Integer(), nullable=False),
            sa.Column("mes", sa.Integer(), nullable=False),
            sa.Column(
                "confirmado_em",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column("ativa", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("invalidada_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("invalidada_motivo", sa.String(500), nullable=True),
            sa.UniqueConstraint(
                "tenant_id",
                "atendente_id",
                "ano",
                "mes",
                name="uq_ponto_espelho_ciencias_atendente_ano_mes",
            ),
        )
        op.create_index("ix_ponto_espelho_ciencias_tenant_id", "ponto_espelho_ciencias", ["tenant_id"])
        op.create_index(
            "ix_ponto_espelho_ciencias_atendente_id",
            "ponto_espelho_ciencias",
            ["atendente_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("ponto_espelho_ciencias"):
        op.drop_table("ponto_espelho_ciencias")
    if insp.has_table("ponto_competencias"):
        op.drop_table("ponto_competencias")
