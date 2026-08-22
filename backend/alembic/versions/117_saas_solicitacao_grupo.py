"""Grupo de pedidos iguais na fila SaaS (peso da demanda).

Revision ID: 117_saas_solicitacao_grupo
Revises: 116_saas_protocolo_unico
Create Date: 2026-08-22
"""

import sqlalchemy as sa
from alembic import op

revision = "117_saas_solicitacao_grupo"
down_revision = "116_saas_protocolo_unico"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("saas_solicitacoes_produto"):
        return
    cols = {c["name"] for c in insp.get_columns("saas_solicitacoes_produto")}
    if "grupo_id" not in cols:
        op.add_column(
            "saas_solicitacoes_produto",
            sa.Column("grupo_id", sa.Integer(), nullable=True),
        )
        op.create_index(
            "ix_saas_solicitacoes_produto_grupo_id",
            "saas_solicitacoes_produto",
            ["grupo_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("saas_solicitacoes_produto"):
        return
    cols = {c["name"] for c in insp.get_columns("saas_solicitacoes_produto")}
    if "grupo_id" in cols:
        op.drop_index("ix_saas_solicitacoes_produto_grupo_id", table_name="saas_solicitacoes_produto")
        op.drop_column("saas_solicitacoes_produto", "grupo_id")
