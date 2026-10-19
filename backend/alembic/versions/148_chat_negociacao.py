"""Chat pode apontar para uma negociação do CRM antes da empresa (#1182).

Revision ID: 148_chat_negociacao
Revises: 147_permissao_grupos
Create Date: 2026-10-15
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "148_chat_negociacao"
down_revision = "147_permissao_grupos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    cols = {c["name"] for c in insp.get_columns("whatsapp_chats")}
    if "negociacao_id" in cols:
        return
    op.add_column("whatsapp_chats", sa.Column("negociacao_id", sa.Integer(), nullable=True))
    op.create_index("ix_whatsapp_chats_negociacao_id", "whatsapp_chats", ["negociacao_id"])
    op.create_foreign_key(
        "fk_whatsapp_chats_negociacao_id",
        "whatsapp_chats",
        "crm_negociacoes",
        ["negociacao_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_whatsapp_chats_negociacao_id", "whatsapp_chats", type_="foreignkey")
    op.drop_index("ix_whatsapp_chats_negociacao_id", table_name="whatsapp_chats")
    op.drop_column("whatsapp_chats", "negociacao_id")
