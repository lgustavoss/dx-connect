"""Solicitações de melhoria / problema a partir dos Release Notes (#799 / #800–#807).

Revision ID: 105_solicitacoes_melhoria
Revises: 104_wpp_mensagem_encaminhada
Create Date: 2026-08-21
"""

import sqlalchemy as sa
from alembic import op

revision = "105_solicitacoes_melhoria"
down_revision = "104_wpp_mensagem_encaminhada"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("solicitacoes_melhoria"):
        op.create_table(
            "solicitacoes_melhoria",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("organizacao_id", sa.Integer(), nullable=False, index=True),
            sa.Column(
                "autor_atendente_id",
                sa.Integer(),
                sa.ForeignKey("atendentes.id", ondelete="SET NULL"),
                nullable=True,
                index=True,
            ),
            sa.Column("autor_nome", sa.String(255), nullable=True),
            sa.Column("tipo", sa.String(32), nullable=False, index=True),
            sa.Column("titulo", sa.String(200), nullable=False),
            sa.Column("descricao", sa.Text(), nullable=False),
            sa.Column("status", sa.String(40), nullable=False, server_default="aberta", index=True),
            sa.Column("motivo_nao_desenvolvimento", sa.Text(), nullable=True),
            sa.Column("versao_contexto", sa.String(64), nullable=True),
            sa.Column("github_repo", sa.String(200), nullable=True),
            sa.Column("github_issue_number", sa.Integer(), nullable=True),
            sa.Column("github_issue_url", sa.String(500), nullable=True),
            sa.Column("github_last_sync_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("github_last_error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not insp.has_table("solicitacoes_melhoria_historico"):
        op.create_table(
            "solicitacoes_melhoria_historico",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "solicitacao_id",
                sa.Integer(),
                sa.ForeignKey("solicitacoes_melhoria.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("status_anterior", sa.String(40), nullable=True),
            sa.Column("status_novo", sa.String(40), nullable=False),
            sa.Column("motivo", sa.Text(), nullable=True),
            sa.Column(
                "atendente_id",
                sa.Integer(),
                sa.ForeignKey("atendentes.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("mensagem_publica", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )

    if not insp.has_table("solicitacoes_melhoria_comentarios"):
        op.create_table(
            "solicitacoes_melhoria_comentarios",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "solicitacao_id",
                sa.Integer(),
                sa.ForeignKey("solicitacoes_melhoria.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("corpo", sa.Text(), nullable=False),
            sa.Column("publico_cliente", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("origem", sa.String(32), nullable=False, server_default="manual"),
            sa.Column(
                "autor_atendente_id",
                sa.Integer(),
                sa.ForeignKey("atendentes.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("autor_nome", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    for table in (
        "solicitacoes_melhoria_comentarios",
        "solicitacoes_melhoria_historico",
        "solicitacoes_melhoria",
    ):
        if insp.has_table(table):
            op.drop_table(table)
