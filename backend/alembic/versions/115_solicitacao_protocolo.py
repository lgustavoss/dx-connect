"""Protocolo #S nas solicitações de melhoria / fila SaaS.

Revision ID: 115_solicitacao_protocolo
Revises: 114_saas_solicitacao_gh
Create Date: 2026-08-22
"""

import sqlalchemy as sa
from alembic import op

revision = "115_solicitacao_protocolo"
down_revision = "114_saas_solicitacao_gh"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("solicitacoes_melhoria"):
        cols = {c["name"] for c in insp.get_columns("solicitacoes_melhoria")}
        if "protocolo" not in cols:
            op.add_column("solicitacoes_melhoria", sa.Column("protocolo", sa.String(32), nullable=True))
            op.execute(
                sa.text(
                    "UPDATE solicitacoes_melhoria SET protocolo = '#S0-' || lpad(id::text, 5, '0') "
                    "WHERE protocolo IS NULL"
                )
            )
            op.alter_column("solicitacoes_melhoria", "protocolo", nullable=False)
            op.create_index(
                "ix_solicitacoes_melhoria_protocolo",
                "solicitacoes_melhoria",
                ["protocolo"],
                unique=True,
            )

    if insp.has_table("saas_solicitacoes_produto"):
        cols = {c["name"] for c in insp.get_columns("saas_solicitacoes_produto")}
        if "protocolo" not in cols:
            op.add_column("saas_solicitacoes_produto", sa.Column("protocolo", sa.String(32), nullable=True))
            op.execute(
                sa.text(
                    "UPDATE saas_solicitacoes_produto SET protocolo = '#S0-' || lpad(origem_solicitacao_id::text, 5, '0') "
                    "WHERE protocolo IS NULL"
                )
            )
            op.create_index(
                "ix_saas_solicitacoes_produto_protocolo",
                "saas_solicitacoes_produto",
                ["protocolo"],
                unique=False,
            )
            op.create_unique_constraint(
                "uq_saas_solicitacoes_produto_protocolo",
                "saas_solicitacoes_produto",
                ["instance_slug", "protocolo"],
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("saas_solicitacoes_produto"):
        cols = {c["name"] for c in insp.get_columns("saas_solicitacoes_produto")}
        if "protocolo" in cols:
            op.drop_constraint(
                "uq_saas_solicitacoes_produto_protocolo",
                "saas_solicitacoes_produto",
                type_="unique",
            )
            op.drop_index("ix_saas_solicitacoes_produto_protocolo", table_name="saas_solicitacoes_produto")
            op.drop_column("saas_solicitacoes_produto", "protocolo")
    if insp.has_table("solicitacoes_melhoria"):
        cols = {c["name"] for c in insp.get_columns("solicitacoes_melhoria")}
        if "protocolo" in cols:
            op.drop_index("ix_solicitacoes_melhoria_protocolo", table_name="solicitacoes_melhoria")
            op.drop_column("solicitacoes_melhoria", "protocolo")
