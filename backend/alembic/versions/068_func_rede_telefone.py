"""funcionarios_rede.telefone para contato WhatsApp outbound (#531).

Revision ID: 068_func_rede_telefone
Revises: 067_portal_chat_avaliacao_midia
Create Date: 2026-07-15
"""

import sqlalchemy as sa
from alembic import op

revision = "068_func_rede_telefone"
down_revision = "067_portal_chat_avaliacao_midia"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("funcionarios_rede", sa.Column("telefone", sa.String(length=20), nullable=True))
    op.create_index("ix_funcionarios_rede_telefone", "funcionarios_rede", ["telefone"])


def downgrade() -> None:
    op.drop_index("ix_funcionarios_rede_telefone", table_name="funcionarios_rede")
    op.drop_column("funcionarios_rede", "telefone")
