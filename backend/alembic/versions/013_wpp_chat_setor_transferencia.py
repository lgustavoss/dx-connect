"""WhatsApp: setor do chat + transferência.

Revision ID: 013_wpp_chat_setor
Revises: 012_wpp_nome_empresa
Create Date: 2026-04-21
"""

from alembic import op
import sqlalchemy as sa


revision = "013_wpp_chat_setor"
down_revision = "012_wpp_nome_empresa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("whatsapp_chats", sa.Column("setor_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_whatsapp_chats_setor_id"), "whatsapp_chats", ["setor_id"], unique=False)
    op.create_foreign_key(
        "fk_whatsapp_chats_setor_id_setores",
        "whatsapp_chats",
        "setores",
        ["setor_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_whatsapp_chats_setor_id_setores", "whatsapp_chats", type_="foreignkey")
    op.drop_index(op.f("ix_whatsapp_chats_setor_id"), table_name="whatsapp_chats")
    op.drop_column("whatsapp_chats", "setor_id")

