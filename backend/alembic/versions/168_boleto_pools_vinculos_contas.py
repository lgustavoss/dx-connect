"""Multi-pool Boleto Cloud + vínculos + contas bancárias (#1392).

Revision ID: 168_boleto_pools_multi
Revises: 167_boleto_pool
Create Date: 2026-11-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "168_boleto_pools_multi"
down_revision = "167_boleto_pool"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("boleto_pools"):
        cols = {c["name"] for c in insp.get_columns("boleto_pools")}
        if "email_login" not in cols:
            op.add_column("boleto_pools", sa.Column("email_login", sa.String(length=255), nullable=True))
        if "faixa_teto" not in cols:
            op.add_column("boleto_pools", sa.Column("faixa_teto", sa.Integer(), nullable=True))
        if "notas" not in cols:
            op.add_column("boleto_pools", sa.Column("notas", sa.Text(), nullable=True))

    if not insp.has_table("boleto_pool_vinculos"):
        op.create_table(
            "boleto_pool_vinculos",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "cliente_saas_id",
                sa.Integer(),
                sa.ForeignKey("clientes_saas.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "pool_id",
                sa.Integer(),
                sa.ForeignKey("boleto_pools.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("vigencia_de", sa.DateTime(timezone=True), nullable=False),
            sa.Column("vigencia_ate", sa.DateTime(timezone=True), nullable=True),
            sa.Column("notas", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_boleto_pool_vinculos_cliente", "boleto_pool_vinculos", ["cliente_saas_id"])
        op.create_index("ix_boleto_pool_vinculos_pool", "boleto_pool_vinculos", ["pool_id"])

    if not insp.has_table("cobranca_contas_bancarias"):
        op.create_table(
            "cobranca_contas_bancarias",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("apelido", sa.String(length=120), nullable=False),
            sa.Column("banco_codigo", sa.String(length=10), nullable=True),
            sa.Column("banco_nome", sa.String(length=120), nullable=True),
            sa.Column("agencia", sa.String(length=20), nullable=True),
            sa.Column("agencia_dv", sa.String(length=4), nullable=True),
            sa.Column("conta", sa.String(length=32), nullable=True),
            sa.Column("conta_dv", sa.String(length=4), nullable=True),
            sa.Column("carteira", sa.String(length=20), nullable=True),
            sa.Column("titular_nome", sa.String(length=200), nullable=True),
            sa.Column("titular_documento", sa.String(length=20), nullable=True),
            sa.Column("boleto_cloud_token_cifrado", sa.Text(), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("padrao", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("notas", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_cobranca_contas_bancarias_id", "cobranca_contas_bancarias", ["id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("cobranca_contas_bancarias"):
        op.drop_index("ix_cobranca_contas_bancarias_id", table_name="cobranca_contas_bancarias")
        op.drop_table("cobranca_contas_bancarias")
    if insp.has_table("boleto_pool_vinculos"):
        op.drop_index("ix_boleto_pool_vinculos_pool", table_name="boleto_pool_vinculos")
        op.drop_index("ix_boleto_pool_vinculos_cliente", table_name="boleto_pool_vinculos")
        op.drop_table("boleto_pool_vinculos")
    if insp.has_table("boleto_pools"):
        cols = {c["name"] for c in insp.get_columns("boleto_pools")}
        for col in ("notas", "faixa_teto", "email_login"):
            if col in cols:
                op.drop_column("boleto_pools", col)
