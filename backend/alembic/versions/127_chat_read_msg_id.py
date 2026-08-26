"""Cursor de leitura WhatsApp/Portal por id de mensagem (#951).

Revision ID: 127_chat_read_msg_id
Revises: 126_ponto_hora_extra
Create Date: 2026-08-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "127_chat_read_msg_id"
down_revision = "126_ponto_hora_extra"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("whatsapp_chat_reads"):
        cols = {c["name"] for c in insp.get_columns("whatsapp_chat_reads")}
        if "last_seen_mensagem_id" not in cols:
            op.add_column(
                "whatsapp_chat_reads",
                sa.Column("last_seen_mensagem_id", sa.Integer(), nullable=True),
            )
    if insp.has_table("portal_chat_reads"):
        cols = {c["name"] for c in insp.get_columns("portal_chat_reads")}
        if "last_seen_mensagem_id" not in cols:
            op.add_column(
                "portal_chat_reads",
                sa.Column("last_seen_mensagem_id", sa.Integer(), nullable=True),
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("whatsapp_chat_reads"):
        cols = {c["name"] for c in insp.get_columns("whatsapp_chat_reads")}
        if "last_seen_mensagem_id" in cols:
            op.drop_column("whatsapp_chat_reads", "last_seen_mensagem_id")
    if insp.has_table("portal_chat_reads"):
        cols = {c["name"] for c in insp.get_columns("portal_chat_reads")}
        if "last_seen_mensagem_id" in cols:
            op.drop_column("portal_chat_reads", "last_seen_mensagem_id")
