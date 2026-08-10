"""Tabela clientes_saas (licenças DeskRudder / control-plane).

Revision ID: 084_cliente_saas
Revises: 083_comercial_custos_tier_posto
Create Date: 2026-07-23
"""

import sqlalchemy as sa
from alembic import op

revision = "084_cliente_saas"
down_revision = "083_comercial_custos_tier_posto"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("clientes_saas"):
        return
    op.create_table(
        "clientes_saas",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="trial"),
        sa.Column("plano", sa.String(length=80), nullable=True),
        sa.Column("data_inicio", sa.Date(), nullable=False),
        sa.Column("data_renovacao", sa.Date(), nullable=True),
        sa.Column("instancia_url", sa.String(length=500), nullable=True),
        sa.Column(
            "provisionamento_solicitado",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("slug", name="uq_clientes_saas_slug"),
    )
    op.create_index("ix_clientes_saas_id", "clientes_saas", ["id"])
    op.create_index("ix_clientes_saas_slug", "clientes_saas", ["slug"])
    op.alter_column("clientes_saas", "status", server_default=None)
    op.alter_column("clientes_saas", "provisionamento_solicitado", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("clientes_saas"):
        return
    op.drop_index("ix_clientes_saas_slug", table_name="clientes_saas")
    op.drop_index("ix_clientes_saas_id", table_name="clientes_saas")
    op.drop_table("clientes_saas")
