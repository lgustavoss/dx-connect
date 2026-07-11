"""Chat interno: ocultação por atendente e janela de edição.

Revision ID: 062_chat_interno_ocultacao
Revises: 061_chat_interno_edicao_reacoes
Create Date: 2026-07-11
"""

import sqlalchemy as sa
from alembic import op

revision = "062_chat_interno_ocultacao"
down_revision = "061_chat_interno_edicao_reacoes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversas_internas_leituras",
        sa.Column("historico_oculto_ate", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "mensagens_internas_ocultas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mensagem_id", sa.Integer(), nullable=False),
        sa.Column("atendente_id", sa.Integer(), nullable=False),
        sa.Column("ocultada_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["atendente_id"], ["atendentes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mensagem_id"], ["mensagens_internas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mensagem_id", "atendente_id", name="uq_mensagens_internas_ocultas"),
    )
    op.create_index("ix_mensagens_internas_ocultas_mensagem_id", "mensagens_internas_ocultas", ["mensagem_id"])
    op.create_index("ix_mensagens_internas_ocultas_atendente_id", "mensagens_internas_ocultas", ["atendente_id"])


def downgrade() -> None:
    op.drop_index("ix_mensagens_internas_ocultas_atendente_id", table_name="mensagens_internas_ocultas")
    op.drop_index("ix_mensagens_internas_ocultas_mensagem_id", table_name="mensagens_internas_ocultas")
    op.drop_table("mensagens_internas_ocultas")
    op.drop_column("conversas_internas_leituras", "historico_oculto_ate")
