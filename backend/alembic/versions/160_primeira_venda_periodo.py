"""Primeira venda no PDV e período coberto da fatura (#1340 / #1341).

Revision ID: 160_primeira_venda_periodo
Revises: 159_faturamento_politica
Create Date: 2026-11-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "160_primeira_venda_periodo"
down_revision = "159_faturamento_politica"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    colunas = {c["name"] for c in insp.get_columns("comercial_contratos")}
    if "primeira_venda_pdv" not in colunas:
        op.add_column("comercial_contratos", sa.Column("primeira_venda_pdv", sa.Date(), nullable=True))
    if "primeira_venda_pdv_por_id" not in colunas:
        op.add_column(
            "comercial_contratos",
            sa.Column(
                "primeira_venda_pdv_por_id",
                sa.Integer(),
                sa.ForeignKey("atendentes.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
    if "primeira_venda_pdv_em" not in colunas:
        op.add_column(
            "comercial_contratos",
            sa.Column("primeira_venda_pdv_em", sa.DateTime(timezone=True), nullable=True),
        )

    colunas_fatura = {c["name"] for c in insp.get_columns("faturamento_faturas")}
    if "periodo_inicio" not in colunas_fatura:
        op.add_column("faturamento_faturas", sa.Column("periodo_inicio", sa.Date(), nullable=True))
    if "periodo_fim" not in colunas_fatura:
        op.add_column("faturamento_faturas", sa.Column("periodo_fim", sa.Date(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    colunas_fatura = {c["name"] for c in insp.get_columns("faturamento_faturas")}
    if "periodo_fim" in colunas_fatura:
        op.drop_column("faturamento_faturas", "periodo_fim")
    if "periodo_inicio" in colunas_fatura:
        op.drop_column("faturamento_faturas", "periodo_inicio")
    colunas = {c["name"] for c in insp.get_columns("comercial_contratos")}
    if "primeira_venda_pdv_em" in colunas:
        op.drop_column("comercial_contratos", "primeira_venda_pdv_em")
    if "primeira_venda_pdv_por_id" in colunas:
        op.drop_column("comercial_contratos", "primeira_venda_pdv_por_id")
    if "primeira_venda_pdv" in colunas:
        op.drop_column("comercial_contratos", "primeira_venda_pdv")
