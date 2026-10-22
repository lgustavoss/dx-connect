"""Renomeia tipo de acesso remoto da frota para DeskRemote.

Revision ID: 153_pdv_tipo_deskremote
Revises: 152_versao_pdv_retaguarda
Create Date: 2026-10-22
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "153_pdv_tipo_deskremote"
down_revision = "152_versao_pdv_retaguarda"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("pdv_tipos_acesso_remoto"):
        return
    op.execute(
        sa.text(
            """
            UPDATE pdv_tipos_acesso_remoto AS t
            SET nome = 'DeskRemote'
            WHERE lower(replace(t.nome, ' ', '')) IN (
                'rustdesk',
                'acessoremoto',
                'deskrudder',
                'deskrudderacessoremoto'
            )
              AND NOT EXISTS (
                SELECT 1
                FROM pdv_tipos_acesso_remoto AS x
                WHERE x.id <> t.id
                  AND lower(replace(x.nome, ' ', '')) IN ('deskremote')
              )
            """
        )
    )


def downgrade() -> None:
    pass
