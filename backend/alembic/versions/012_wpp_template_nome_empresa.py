"""WhatsApp: nome da empresa para templates.

Revision ID: 012_wpp_nome_empresa
Revises: 011_wpp_horarios
Create Date: 2026-04-21
"""

from alembic import op
import sqlalchemy as sa


revision = "012_wpp_nome_empresa"
down_revision = "011_wpp_horarios"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("whatsapp_settings", sa.Column("nome_empresa_exibicao", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("whatsapp_settings", "nome_empresa_exibicao")

