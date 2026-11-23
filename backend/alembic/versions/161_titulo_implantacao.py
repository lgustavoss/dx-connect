"""Setup vira título próprio e tipo do título a receber (#1342).

Revision ID: 161_titulo_implantacao
Revises: 160_primeira_venda_periodo
Create Date: 2026-11-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "161_titulo_implantacao"
down_revision = "160_primeira_venda_periodo"
branch_labels = None
depends_on = None

INDICE_IMPLANTACAO = "uq_faturamento_titulo_implantacao_contrato"


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    colunas_contrato = {c["name"] for c in insp.get_columns("comercial_contratos")}
    if "setup_momento" not in colunas_contrato:
        op.add_column("comercial_contratos", sa.Column("setup_momento", sa.String(32), nullable=True))
    if "setup_data_combinada" not in colunas_contrato:
        op.add_column("comercial_contratos", sa.Column("setup_data_combinada", sa.Date(), nullable=True))

    colunas = {c["name"]: c for c in insp.get_columns("faturamento_titulos")}
    if "tipo" not in colunas:
        op.add_column(
            "faturamento_titulos",
            sa.Column("tipo", sa.String(20), nullable=False, server_default="mensalidade"),
        )
        op.execute(sa.text("UPDATE faturamento_titulos SET tipo = 'mensalidade' WHERE tipo IS NULL"))
    if not colunas.get("fatura_id", {}).get("nullable", True):
        op.alter_column("faturamento_titulos", "fatura_id", existing_type=sa.Integer(), nullable=True)

    indices = {i["name"] for i in insp.get_indexes("faturamento_titulos")}
    if INDICE_IMPLANTACAO not in indices:
        op.create_index(
            INDICE_IMPLANTACAO,
            "faturamento_titulos",
            ["contrato_id"],
            unique=True,
            postgresql_where=sa.text("tipo = 'implantacao'"),
            sqlite_where=sa.text("tipo = 'implantacao'"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    indices = {i["name"] for i in insp.get_indexes("faturamento_titulos")}
    if INDICE_IMPLANTACAO in indices:
        op.drop_index(INDICE_IMPLANTACAO, table_name="faturamento_titulos")
    op.execute(sa.text("DELETE FROM faturamento_titulos WHERE tipo = 'implantacao'"))
    colunas = {c["name"]: c for c in insp.get_columns("faturamento_titulos")}
    if "tipo" in colunas:
        op.drop_column("faturamento_titulos", "tipo")
    if colunas.get("fatura_id", {}).get("nullable", True):
        op.alter_column("faturamento_titulos", "fatura_id", existing_type=sa.Integer(), nullable=False)
    colunas_contrato = {c["name"] for c in insp.get_columns("comercial_contratos")}
    if "setup_data_combinada" in colunas_contrato:
        op.drop_column("comercial_contratos", "setup_data_combinada")
    if "setup_momento" in colunas_contrato:
        op.drop_column("comercial_contratos", "setup_momento")
