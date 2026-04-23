"""whatsapp_mensagens: tipo de mídia, mimetype e ficheiro local.

Revision ID: 008_whatsapp_mensagem_midia
Revises: 007_whatsapp_evolution
Create Date: 2026-04-21
"""

from alembic import op
import sqlalchemy as sa


revision = "008_whatsapp_mensagem_midia"
down_revision = "007_whatsapp_evolution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("whatsapp_mensagens", sa.Column("tipo_midia", sa.String(length=24), nullable=True))
    op.add_column("whatsapp_mensagens", sa.Column("mimetype", sa.String(length=128), nullable=True))
    op.add_column(
        "whatsapp_mensagens",
        sa.Column("midia_nome_arquivo", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("whatsapp_mensagens", "midia_nome_arquivo")
    op.drop_column("whatsapp_mensagens", "mimetype")
    op.drop_column("whatsapp_mensagens", "tipo_midia")
