"""Issue GitHub ligada à fila SaaS (MCP Cursor).

Revision ID: 114_saas_solicitacao_gh
Revises: 113_saas_solicitacao_anexos
Create Date: 2026-08-22
"""

import sqlalchemy as sa
from alembic import op

revision = "114_saas_solicitacao_gh"
down_revision = "113_saas_solicitacao_anexos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("saas_solicitacoes_produto"):
        return
    cols = {c["name"] for c in insp.get_columns("saas_solicitacoes_produto")}
    if "github_repo" not in cols:
        op.add_column("saas_solicitacoes_produto", sa.Column("github_repo", sa.String(200), nullable=True))
    if "github_issue_number" not in cols:
        op.add_column("saas_solicitacoes_produto", sa.Column("github_issue_number", sa.Integer(), nullable=True))
    if "github_issue_url" not in cols:
        op.add_column("saas_solicitacoes_produto", sa.Column("github_issue_url", sa.String(500), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("saas_solicitacoes_produto"):
        return
    cols = {c["name"] for c in insp.get_columns("saas_solicitacoes_produto")}
    for name in ("github_issue_url", "github_issue_number", "github_repo"):
        if name in cols:
            op.drop_column("saas_solicitacoes_produto", name)
