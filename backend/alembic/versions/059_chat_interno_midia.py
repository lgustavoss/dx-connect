"""Chat interno: mídia nas mensagens (#495).

Revision ID: 059_chat_interno_midia
Revises: 058_chat_interno
Create Date: 2026-07-10
"""

import sqlalchemy as sa
from alembic import op

revision = "059_chat_interno_midia"
down_revision = "058_chat_interno"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mensagens_internas",
        sa.Column("tipo_midia", sa.String(length=24), server_default="texto", nullable=False),
    )
    op.add_column("mensagens_internas", sa.Column("mimetype", sa.String(length=128), nullable=True))
    op.add_column("mensagens_internas", sa.Column("nome_arquivo", sa.String(length=500), nullable=True))
    op.add_column("mensagens_internas", sa.Column("storage_key", sa.String(length=255), nullable=True))
    op.add_column("mensagens_internas", sa.Column("tamanho_bytes", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_mensagens_internas_tipo_midia"), "mensagens_internas", ["tipo_midia"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_mensagens_internas_tipo_midia"), table_name="mensagens_internas")
    op.drop_column("mensagens_internas", "tamanho_bytes")
    op.drop_column("mensagens_internas", "storage_key")
    op.drop_column("mensagens_internas", "nome_arquivo")
    op.drop_column("mensagens_internas", "mimetype")
    op.drop_column("mensagens_internas", "tipo_midia")
