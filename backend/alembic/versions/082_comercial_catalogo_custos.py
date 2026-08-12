"""Catálogo comercial: salário mínimo e itens de custo (#321).

Revision ID: 082_comercial_catalogo_custos
Revises: 081_wpp_demanda_motivo_sugestoes
Create Date: 2026-08-03
"""

import sqlalchemy as sa
from alembic import op

revision = "082_comercial_catalogo_custos"
down_revision = "081_wpp_demanda_motivo_sugestoes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("salario_minimo_referencia"):
        op.create_table(
            "salario_minimo_referencia",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("valor", sa.Numeric(12, 2), nullable=False),
            sa.Column("vigencia_inicio", sa.Date(), nullable=False),
            sa.Column("vigencia_fim", sa.Date(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(
            "ix_salario_minimo_referencia_vigencia_inicio",
            "salario_minimo_referencia",
            ["vigencia_inicio"],
        )
        op.create_index(
            "ix_salario_minimo_referencia_vigencia_fim",
            "salario_minimo_referencia",
            ["vigencia_fim"],
        )

    if not insp.has_table("custo_catalogo_itens"):
        op.create_table(
            "custo_catalogo_itens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("nome", sa.String(120), nullable=False),
            sa.Column("slug", sa.String(50), nullable=False),
            sa.Column("descricao", sa.Text(), nullable=True),
            sa.Column("tipo", sa.String(24), nullable=False),
            sa.Column("percentual_sm", sa.Numeric(8, 4), nullable=True),
            sa.Column("valor_fixo", sa.Numeric(12, 2), nullable=True),
            sa.Column("tef_base", sa.Numeric(12, 2), nullable=True),
            sa.Column("tef_adicional", sa.Numeric(12, 2), nullable=True),
            sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("vigencia_inicio", sa.Date(), nullable=True),
            sa.Column("vigencia_fim", sa.Date(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("slug", name="uq_custo_catalogo_item_slug"),
        )
        op.create_index("ix_custo_catalogo_itens_slug", "custo_catalogo_itens", ["slug"])
        op.create_index("ix_custo_catalogo_itens_tipo", "custo_catalogo_itens", ["tipo"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("custo_catalogo_itens"):
        op.drop_table("custo_catalogo_itens")
    if insp.has_table("salario_minimo_referencia"):
        op.drop_table("salario_minimo_referencia")
