"""Histórico de triagem da fila SaaS (#881).

Revision ID: 137_saas_hist_triagem_881
Revises: 136_saas_alertas_ops_1036
Create Date: 2026-09-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "137_saas_hist_triagem_881"
down_revision = "136_saas_alertas_ops_1036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "saas_solicitacoes_produto",
        sa.Column("ultimo_ator_nome", sa.String(length=255), nullable=True),
    )
    op.create_table(
        "saas_solicitacoes_produto_historico",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "solicitacao_id",
            sa.Integer(),
            sa.ForeignKey("saas_solicitacoes_produto.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status_anterior", sa.String(length=40), nullable=True),
        sa.Column("status_novo", sa.String(length=40), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column(
            "atendente_id",
            sa.Integer(),
            sa.ForeignKey("atendentes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("autor_nome", sa.String(length=255), nullable=True),
        sa.Column("canal", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_saas_solicitacoes_produto_historico_solicitacao_id",
        "saas_solicitacoes_produto_historico",
        ["solicitacao_id"],
    )
    # Cópias já na instância: o cliente deixa de ver o nome de quem triou.
    op.execute(
        "UPDATE solicitacoes_melhoria_comentarios "
        "SET autor_nome = 'Desenvolvedor' "
        "WHERE origem = 'saas' AND COALESCE(autor_nome, '') != 'Desenvolvedor'"
    )
    op.execute(
        "UPDATE solicitacoes_melhoria_historico "
        "SET atendente_id = NULL "
        "WHERE atendente_id IN (SELECT id FROM atendentes WHERE role = 'saas_ops')"
    )


def downgrade() -> None:
    op.drop_index(
        "ix_saas_solicitacoes_produto_historico_solicitacao_id",
        table_name="saas_solicitacoes_produto_historico",
    )
    op.drop_table("saas_solicitacoes_produto_historico")
    op.drop_column("saas_solicitacoes_produto", "ultimo_ator_nome")
