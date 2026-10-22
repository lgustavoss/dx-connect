"""Renomeia tipo de acesso remoto da frota para DeskRudder.

Revision ID: 150_pdv_tipo_deskrudder
Revises: 149_rustdesk_peers
Create Date: 2026-10-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "150_pdv_tipo_deskrudder"
down_revision = "149_rustdesk_peers"
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
            SET nome = 'DeskRudder'
            WHERE lower(replace(t.nome, ' ', '')) IN ('rustdesk', 'acessoremoto')
              AND NOT EXISTS (
                SELECT 1
                FROM pdv_tipos_acesso_remoto AS x
                WHERE x.id <> t.id
                  AND lower(replace(x.nome, ' ', '')) IN ('deskrudder', 'deskrudderacessoremoto')
              )
            """
        )
    )


def downgrade() -> None:
    pass
