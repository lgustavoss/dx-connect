"""Backfill canais internos por setor ativo (#916).

Revision ID: 119_chat_canal_setor_backfill
Revises: 118_saas_ops_mcp_token
Create Date: 2026-08-24
"""

import sqlalchemy as sa
from alembic import op

revision = "119_chat_canal_setor_backfill"
down_revision = "118_saas_ops_mcp_token"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("setores") or not insp.has_table("conversas_internas"):
        return
    op.execute(
        sa.text(
            """
            INSERT INTO conversas_internas (tenant_id, tipo, titulo, setor_id)
            SELECT s.tenant_id, 'setor', s.nome, s.id
            FROM setores s
            WHERE s.ativo IS TRUE
              AND NOT EXISTS (
                SELECT 1
                FROM conversas_internas c
                WHERE c.tenant_id = s.tenant_id
                  AND c.tipo = 'setor'
                  AND c.setor_id = s.id
              )
            """
        )
    )


def downgrade() -> None:
    # Não remove canais criados pelo backfill — podem ter mensagens.
    pass
