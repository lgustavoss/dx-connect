"""Hora extra para pegar WhatsApp após jornada (#965).

Revision ID: 126_ponto_hora_extra
Revises: 125_ponto_locais_atendente
Create Date: 2026-08-26
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "126_ponto_hora_extra"
down_revision = "125_ponto_locais_atendente"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("ponto_hora_extra"):
        return
    op.create_table(
        "ponto_hora_extra",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id",
            sa.Integer(),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "atendente_id",
            sa.Integer(),
            sa.ForeignKey("atendentes.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("estado", sa.String(20), nullable=False, server_default="pendente"),
        sa.Column("motivo", sa.String(1000), nullable=True),
        sa.Column("modo", sa.String(20), nullable=True),
        sa.Column("ate_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "decidido_por_id",
            sa.Integer(),
            sa.ForeignKey("atendentes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("decidido_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decisao_motivo", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("ponto_hora_extra"):
        op.drop_table("ponto_hora_extra")
