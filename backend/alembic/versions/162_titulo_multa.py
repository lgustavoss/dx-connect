"""Multa de rescisão vira título a receber, uma por contrato (#1386).

Aditiva: a coluna `tipo` e o `fatura_id` opcional nasceram no #1342
(161_titulo_implantacao). Aqui só entra o índice único parcial que garante
uma multa por contrato — a idempotência da rescisão também é checada no
service antes de inserir.

Revision ID: 162_titulo_multa
Revises: 161_titulo_implantacao
Create Date: 2026-11-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "162_titulo_multa"
down_revision = "161_titulo_implantacao"
branch_labels = None
depends_on = None

INDICE_MULTA = "uq_faturamento_titulo_multa_contrato"


def _indices() -> set[str]:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "faturamento_titulos" not in insp.get_table_names():
        return set()
    return {i["name"] for i in insp.get_indexes("faturamento_titulos")}


def upgrade() -> None:
    if INDICE_MULTA not in _indices():
        op.create_index(
            INDICE_MULTA,
            "faturamento_titulos",
            ["contrato_id"],
            unique=True,
            postgresql_where=sa.text("tipo = 'multa'"),
            sqlite_where=sa.text("tipo = 'multa'"),
        )


def downgrade() -> None:
    if INDICE_MULTA in _indices():
        op.drop_index(INDICE_MULTA, table_name="faturamento_titulos")
