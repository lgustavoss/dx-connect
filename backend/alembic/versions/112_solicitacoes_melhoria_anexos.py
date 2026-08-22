"""Anexos e prints nas solicitações de melhoria.

Revision ID: 112_solicitacoes_melhoria_anexos
Revises: 111_saas_solicitacoes_triagem
Create Date: 2026-08-22
"""

import sqlalchemy as sa
from alembic import op

revision = "112_solicitacoes_melhoria_anexos"
down_revision = "111_saas_solicitacoes_triagem"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("solicitacoes_melhoria_anexos"):
        return
    op.create_table(
        "solicitacoes_melhoria_anexos",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "solicitacao_id",
            sa.Integer(),
            sa.ForeignKey("solicitacoes_melhoria.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("autor_atendente_id", sa.Integer(), sa.ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True),
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
    )
    op.create_index(
        "ix_solicitacoes_melhoria_anexos_storage_key",
        "solicitacoes_melhoria_anexos",
        ["storage_key"],
        unique=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("solicitacoes_melhoria_anexos"):
        op.drop_index("ix_solicitacoes_melhoria_anexos_storage_key", table_name="solicitacoes_melhoria_anexos")
        op.drop_table("solicitacoes_melhoria_anexos")
