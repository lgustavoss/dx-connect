"""Complemento do autor na fila SaaS (#1099).

Revision ID: 138_saas_comentario_origem_1099
Revises: 137_saas_hist_triagem_881
Create Date: 2026-09-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "138_saas_comentario_origem_1099"
down_revision = "137_saas_hist_triagem_881"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "saas_solicitacoes_produto_comentarios",
        sa.Column("origem_externa_id", sa.String(length=80), nullable=True),
    )
    op.create_index(
        "ix_saas_solicitacoes_produto_comentarios_origem_externa_id",
        "saas_solicitacoes_produto_comentarios",
        ["origem_externa_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_saas_solicitacoes_produto_comentarios_origem_externa_id",
        table_name="saas_solicitacoes_produto_comentarios",
    )
    op.drop_column("saas_solicitacoes_produto_comentarios", "origem_externa_id")
