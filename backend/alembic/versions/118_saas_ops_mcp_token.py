"""Token Cursor MCP pessoal por saas_ops (#915).

Revision ID: 118_saas_ops_mcp_token
Revises: 117_saas_solicitacao_grupo
Create Date: 2026-08-24
"""

import sqlalchemy as sa
from alembic import op

revision = "118_saas_ops_mcp_token"
down_revision = "117_saas_solicitacao_grupo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("atendentes"):
        return
    cols = {c["name"] for c in insp.get_columns("atendentes")}
    if "mcp_token_hash" not in cols:
        op.add_column(
            "atendentes",
            sa.Column("mcp_token_hash", sa.String(length=64), nullable=True),
        )
        op.create_index("ix_atendentes_mcp_token_hash", "atendentes", ["mcp_token_hash"], unique=True)
    if "mcp_token_gerado_em" not in cols:
        op.add_column(
            "atendentes",
            sa.Column("mcp_token_gerado_em", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("atendentes"):
        return
    cols = {c["name"] for c in insp.get_columns("atendentes")}
    if "mcp_token_gerado_em" in cols:
        op.drop_column("atendentes", "mcp_token_gerado_em")
    if "mcp_token_hash" in cols:
        op.drop_index("ix_atendentes_mcp_token_hash", table_name="atendentes")
        op.drop_column("atendentes", "mcp_token_hash")
