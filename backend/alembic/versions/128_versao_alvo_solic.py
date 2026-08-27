"""versao_alvo nas solicitações SaaS e instância (#955).

Revision ID: 128_versao_alvo_solic
Revises: 127_chat_read_msg_id
Create Date: 2026-08-26
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "128_versao_alvo_solic"
down_revision = "127_chat_read_msg_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "saas_solicitacoes_produto",
        sa.Column("versao_alvo", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "solicitacoes_melhoria",
        sa.Column("versao_alvo", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("solicitacoes_melhoria", "versao_alvo")
    op.drop_column("saas_solicitacoes_produto", "versao_alvo")
