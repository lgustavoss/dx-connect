"""Fatura interna e flag emite_nfse na empresa (#326 / #363 / #364).

Revision ID: 106_faturamento_fatura
Revises: 105_solicitacoes_melhoria
Create Date: 2026-08-21
"""

import sqlalchemy as sa
from alembic import op

revision = "106_faturamento_fatura"
down_revision = "105_solicitacoes_melhoria"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("empresas"):
        cols = {c["name"] for c in insp.get_columns("empresas")}
        if "emite_nfse" not in cols:
            op.add_column(
                "empresas",
                sa.Column("emite_nfse", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            )

    if not insp.has_table("faturamento_faturas"):
        op.create_table(
            "faturamento_faturas",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
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
            sa.Column("emite_nfse", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("status", sa.String(32), nullable=False, server_default="aguardando_aprovacao"),
            sa.Column("rejeicao_motivo", sa.Text(), nullable=True),
            sa.Column("gerada_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column(
                "aprovada_por_id",
                sa.Integer(),
                sa.ForeignKey("atendentes.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("aprovada_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("contrato_id", "competencia", name="uq_faturamento_fatura_contrato_competencia"),
        )
        op.create_index("ix_faturamento_faturas_contrato_id", "faturamento_faturas", ["contrato_id"])
        op.create_index("ix_faturamento_faturas_empresa_id", "faturamento_faturas", ["empresa_id"])
        op.create_index("ix_faturamento_faturas_competencia", "faturamento_faturas", ["competencia"])
        op.create_index("ix_faturamento_faturas_status", "faturamento_faturas", ["status"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("faturamento_faturas"):
        op.drop_table("faturamento_faturas")
    if insp.has_table("empresas"):
        cols = {c["name"] for c in insp.get_columns("empresas")}
        if "emite_nfse" in cols:
            op.drop_column("empresas", "emite_nfse")
