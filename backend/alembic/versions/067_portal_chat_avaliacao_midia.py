"""Portal chat: avaliação e mídia nas mensagens.

Revision ID: 067_portal_chat_avaliacao_midia
Revises: 066_portal_chat_demandas
Create Date: 2026-07-12
"""

import sqlalchemy as sa
from alembic import op

revision = "067_portal_chat_avaliacao_midia"
down_revision = "066_portal_chat_demandas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("portal_chats", sa.Column("avaliacao_nota", sa.Integer(), nullable=True))
    op.add_column("portal_chats", sa.Column("avaliacao_respondida_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "portal_chats",
        sa.Column("avaliacao_solicitada", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.add_column(
        "portal_mensagens",
        sa.Column("tipo_midia", sa.String(length=24), nullable=False, server_default="texto"),
    )
    op.add_column("portal_mensagens", sa.Column("mimetype", sa.String(length=128), nullable=True))
    op.add_column("portal_mensagens", sa.Column("midia_nome_arquivo", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("portal_mensagens", "midia_nome_arquivo")
    op.drop_column("portal_mensagens", "mimetype")
    op.drop_column("portal_mensagens", "tipo_midia")
    op.drop_column("portal_chats", "avaliacao_solicitada")
    op.drop_column("portal_chats", "avaliacao_respondida_at")
    op.drop_column("portal_chats", "avaliacao_nota")
