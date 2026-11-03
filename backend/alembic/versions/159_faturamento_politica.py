"""Política de faturamento por instância (#1339).

Revision ID: 159_faturamento_politica
Revises: 158_crm_origens_lead
Create Date: 2026-11-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "159_faturamento_politica"
down_revision = "158_crm_origens_lead"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("faturamento_politica"):
        op.create_table(
            "faturamento_politica",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("dia_vencimento", sa.Integer(), nullable=False, server_default="10"),
            sa.Column("gatilho", sa.String(32), nullable=False, server_default="data_inicio"),
            sa.Column("gatilho_dias", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "proporcional_primeira_fatura",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        # Semente = perfil de hoje: dia 10, mensalidade na data_inicio, primeira cheia.
        bind.execute(
            sa.text(
                """
                INSERT INTO faturamento_politica
                    (id, dia_vencimento, gatilho, gatilho_dias, proporcional_primeira_fatura)
                SELECT 1, 10, 'data_inicio', 0, false
                WHERE NOT EXISTS (SELECT 1 FROM faturamento_politica WHERE id = 1)
                """
            )
        )

    colunas = {c["name"] for c in insp.get_columns("comercial_contratos")}
    if "dia_vencimento_override" not in colunas:
        op.add_column("comercial_contratos", sa.Column("dia_vencimento_override", sa.Integer(), nullable=True))
    if "inicio_mensalidade_override" not in colunas:
        op.add_column("comercial_contratos", sa.Column("inicio_mensalidade_override", sa.Date(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("comercial_contratos"):
        colunas = {c["name"] for c in insp.get_columns("comercial_contratos")}
        if "inicio_mensalidade_override" in colunas:
            op.drop_column("comercial_contratos", "inicio_mensalidade_override")
        if "dia_vencimento_override" in colunas:
            op.drop_column("comercial_contratos", "dia_vencimento_override")
    if insp.has_table("faturamento_politica"):
        op.drop_table("faturamento_politica")
