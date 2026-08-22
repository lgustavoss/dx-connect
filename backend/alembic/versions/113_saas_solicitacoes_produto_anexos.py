"""Anexos da fila SaaS de solicitações (cópia da mídia das instâncias).

Revision ID: 113_saas_solicitacao_anexos
Revises: 112_solicitacoes_melhoria_anexos
Create Date: 2026-08-22
"""

import sqlalchemy as sa
from alembic import op

revision = "113_saas_solicitacao_anexos"
down_revision = "112_solicitacoes_melhoria_anexos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("saas_solicitacoes_produto_anexos"):
        return
    op.create_table(
        "saas_solicitacoes_produto_anexos",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "solicitacao_id",
            sa.Integer(),
            sa.ForeignKey("saas_solicitacoes_produto.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("papel", sa.String(16), nullable=False, server_default="anexo"),
        sa.Column("nome_original", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=True),
        sa.Column("tamanho_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(80), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "solicitacao_id",
            "storage_key",
            name="uq_saas_solicitacoes_produto_anexos_key",
        ),
    )
    op.create_index(
        "ix_saas_solicitacoes_produto_anexos_storage_key",
        "saas_solicitacoes_produto_anexos",
        ["storage_key"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("saas_solicitacoes_produto_anexos"):
        op.drop_index(
            "ix_saas_solicitacoes_produto_anexos_storage_key",
            table_name="saas_solicitacoes_produto_anexos",
        )
        op.drop_table("saas_solicitacoes_produto_anexos")
