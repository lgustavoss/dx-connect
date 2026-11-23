"""Títulos a receber na aprovação da fatura (#328 / #373).

Revision ID: 156_faturamento_titulos
Revises: 155_faturamento_anexos
Create Date: 2026-10-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "156_faturamento_titulos"
down_revision = "155_faturamento_anexos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("faturamento_titulos"):
        return
    op.create_table(
        "faturamento_titulos",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "fatura_id",
            sa.Integer(),
            sa.ForeignKey("faturamento_faturas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "contrato_id",
            sa.Integer(),
            sa.ForeignKey("comercial_contratos.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "empresa_id",
            sa.Integer(),
            sa.ForeignKey("empresas.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("competencia", sa.String(7), nullable=False),
        sa.Column("valor", sa.Numeric(14, 2), nullable=False),
        sa.Column("vencimento", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="aberto"),
        sa.Column("pago_em", sa.Date(), nullable=True),
        sa.Column("valor_pago", sa.Numeric(14, 2), nullable=True),
        sa.Column("baixa_observacao", sa.Text(), nullable=True),
        sa.Column(
            "baixado_por_id",
            sa.Integer(),
            sa.ForeignKey("atendentes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("baixado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("fatura_id", name="uq_faturamento_titulo_fatura"),
    )
    op.create_index("ix_faturamento_titulos_contrato_id", "faturamento_titulos", ["contrato_id"])
    op.create_index("ix_faturamento_titulos_empresa_id", "faturamento_titulos", ["empresa_id"])
    op.create_index("ix_faturamento_titulos_competencia", "faturamento_titulos", ["competencia"])
    op.create_index("ix_faturamento_titulos_vencimento", "faturamento_titulos", ["vencimento"])
    op.create_index("ix_faturamento_titulos_status", "faturamento_titulos", ["status"])

    if insp.has_table("faturamento_faturas"):
        op.execute(
            sa.text(
                """
                INSERT INTO faturamento_titulos
                    (fatura_id, contrato_id, empresa_id, competencia, valor, vencimento, status)
                SELECT id, contrato_id, empresa_id, competencia, valor, vencimento, 'aberto'
                FROM faturamento_faturas
                WHERE status = 'aprovada'
                """
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("faturamento_titulos"):
        op.drop_table("faturamento_titulos")
