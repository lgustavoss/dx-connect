"""Chat interno: edição/apagamento de mensagem e reações.

Revision ID: 061_chat_interno_edicao_reacoes
Revises: 060_mensagem_status
Create Date: 2026-07-11
"""

import sqlalchemy as sa
from alembic import op

revision = "061_chat_interno_edicao_reacoes"
down_revision = "060_mensagem_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mensagens_internas",
        sa.Column("editada_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "mensagens_internas",
        sa.Column("apagada_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "mensagens_internas_reacoes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mensagem_id", sa.Integer(), nullable=False),
        sa.Column("atendente_id", sa.Integer(), nullable=False),
        sa.Column("emoji", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["atendente_id"], ["atendentes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mensagem_id"], ["mensagens_internas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mensagem_id", "atendente_id", name="uq_mensagens_internas_reacoes_mensagem_atendente"),
    )
    op.create_index(
        "ix_mensagens_internas_reacoes_mensagem_id",
        "mensagens_internas_reacoes",
        ["mensagem_id"],
    )
    op.create_index(
        "ix_mensagens_internas_reacoes_atendente_id",
        "mensagens_internas_reacoes",
        ["atendente_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_mensagens_internas_reacoes_atendente_id", table_name="mensagens_internas_reacoes")
    op.drop_index("ix_mensagens_internas_reacoes_mensagem_id", table_name="mensagens_internas_reacoes")
    op.drop_table("mensagens_internas_reacoes")
    op.drop_column("mensagens_internas", "apagada_em")
    op.drop_column("mensagens_internas", "editada_em")
