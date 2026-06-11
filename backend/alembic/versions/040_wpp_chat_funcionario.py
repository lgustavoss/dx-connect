"""WhatsApp: vínculo chat ↔ funcionário da rede.

Revision ID: 040_wpp_chat_funcionario
Revises: 039_wpp_avaliacao_solicitada
Create Date: 2026-06-11
"""

from alembic import op
import sqlalchemy as sa

revision = "040_wpp_chat_funcionario"
down_revision = "039_wpp_avaliacao_solicitada"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "whatsapp_chats",
        sa.Column("funcionario_rede_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "whatsapp_chats",
        sa.Column("empresa_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_whatsapp_chats_funcionario_rede_id",
        "whatsapp_chats",
        "funcionarios_rede",
        ["funcionario_rede_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_whatsapp_chats_empresa_id",
        "whatsapp_chats",
        "empresas",
        ["empresa_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_whatsapp_chats_funcionario_rede_id", "whatsapp_chats", ["funcionario_rede_id"])
    op.create_index("ix_whatsapp_chats_empresa_id", "whatsapp_chats", ["empresa_id"])


def downgrade() -> None:
    op.drop_index("ix_whatsapp_chats_empresa_id", table_name="whatsapp_chats")
    op.drop_index("ix_whatsapp_chats_funcionario_rede_id", table_name="whatsapp_chats")
    op.drop_constraint("fk_whatsapp_chats_empresa_id", "whatsapp_chats", type_="foreignkey")
    op.drop_constraint("fk_whatsapp_chats_funcionario_rede_id", "whatsapp_chats", type_="foreignkey")
    op.drop_column("whatsapp_chats", "empresa_id")
    op.drop_column("whatsapp_chats", "funcionario_rede_id")
