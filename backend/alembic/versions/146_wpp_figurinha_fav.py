"""Galeria de figurinhas por atendente (#S202610-0001).

Revision ID: 146_wpp_figurinha_fav
Revises: 145_ponto_feriado_rec
Create Date: 2026-10-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "146_wpp_figurinha_fav"
down_revision = "145_ponto_feriado_rec"
branch_labels = None
depends_on = None

TABELA = "whatsapp_figurinhas_favoritas"


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if insp.has_table(TABELA):
        return
    op.create_table(
        TABELA,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "atendente_id",
            sa.Integer(),
            sa.ForeignKey("atendentes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("arquivo_nome", sa.String(length=500), nullable=False),
        sa.Column("mimetype", sa.String(length=128), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("atendente_id", "sha256", name="uq_wpp_figurinha_fav_atendente_sha256"),
    )
    op.create_index(f"ix_{TABELA}_id", TABELA, ["id"])
    op.create_index(f"ix_{TABELA}_atendente_id", TABELA, ["atendente_id"])


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if insp.has_table(TABELA):
        op.drop_table(TABELA)
