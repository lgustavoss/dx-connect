"""Pool Boleto Cloud no control-plane (#1392).

Revision ID: 167_boleto_pool
Revises: 166_deskremote_update_pedido
Create Date: 2026-11-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "167_boleto_pool"
down_revision = "166_deskremote_update_pedido"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("boleto_pools"):
        return
    op.create_table(
        "boleto_pools",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("apelido", sa.String(length=120), nullable=False),
        sa.Column(
            "api_base_url",
            sa.String(length=255),
            nullable=False,
            server_default="https://sandbox.boletocloud.com/api/v1",
        ),
        sa.Column("api_key_cifrada", sa.Text(), nullable=True),
        sa.Column("conta_token_cifrado", sa.Text(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_boleto_pools_id", "boleto_pools", ["id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("boleto_pools"):
        return
    op.drop_index("ix_boleto_pools_id", table_name="boleto_pools")
    op.drop_table("boleto_pools")
