"""Triagem SaaS: comentários no control-plane + origem externa na instância (#856).

Revision ID: 111_saas_solicitacoes_triagem
Revises: 110_saas_solicitacoes_produto
Create Date: 2026-08-22
"""

import sqlalchemy as sa
from alembic import op

revision = "111_saas_solicitacoes_triagem"
down_revision = "110_saas_solicitacoes_produto"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("saas_solicitacoes_produto"):
        cols = {c["name"] for c in insp.get_columns("saas_solicitacoes_produto")}
        if "motivo_nao_desenvolvimento" not in cols:
            op.add_column(
                "saas_solicitacoes_produto",
                sa.Column("motivo_nao_desenvolvimento", sa.Text(), nullable=True),
            )
        if "triagem_atualizada_em" not in cols:
            op.add_column(
                "saas_solicitacoes_produto",
                sa.Column("triagem_atualizada_em", sa.DateTime(timezone=True), nullable=True),
            )

    if not insp.has_table("saas_solicitacoes_produto_comentarios"):
        op.create_table(
            "saas_solicitacoes_produto_comentarios",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "solicitacao_id",
                sa.Integer(),
                sa.ForeignKey("saas_solicitacoes_produto.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("corpo", sa.Text(), nullable=False),
            sa.Column("publico_cliente", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("autor_atendente_id", sa.Integer(), nullable=True),
            sa.Column("autor_nome", sa.String(255), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    if insp.has_table("solicitacoes_melhoria_comentarios"):
        cols = {c["name"] for c in insp.get_columns("solicitacoes_melhoria_comentarios")}
        if "origem_externa_id" not in cols:
            op.add_column(
                "solicitacoes_melhoria_comentarios",
                sa.Column("origem_externa_id", sa.String(80), nullable=True),
            )
            op.create_index(
                "ix_solicitacoes_melhoria_comentarios_origem_ext",
                "solicitacoes_melhoria_comentarios",
                ["origem_externa_id"],
                unique=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("solicitacoes_melhoria_comentarios"):
        cols = {c["name"] for c in insp.get_columns("solicitacoes_melhoria_comentarios")}
        if "origem_externa_id" in cols:
            op.drop_index(
                "ix_solicitacoes_melhoria_comentarios_origem_ext",
                table_name="solicitacoes_melhoria_comentarios",
            )
            op.drop_column("solicitacoes_melhoria_comentarios", "origem_externa_id")
    if insp.has_table("saas_solicitacoes_produto_comentarios"):
        op.drop_table("saas_solicitacoes_produto_comentarios")
    if insp.has_table("saas_solicitacoes_produto"):
        cols = {c["name"] for c in insp.get_columns("saas_solicitacoes_produto")}
        for name in ("triagem_atualizada_em", "motivo_nao_desenvolvimento"):
            if name in cols:
                op.drop_column("saas_solicitacoes_produto", name)
