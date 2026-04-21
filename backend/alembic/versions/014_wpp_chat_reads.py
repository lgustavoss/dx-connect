"""WhatsApp: leituras por atendente (não lidas).

Revision ID: 014_wpp_reads
Revises: 013_wpp_chat_setor
Create Date: 2026-04-21
"""

from alembic import op
import sqlalchemy as sa


# IDs curtos (alembic_version.version_num tem limite de 32 chars)
revision = "014_wpp_reads"
down_revision = "013_wpp_chat_setor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("whatsapp_chat_reads"):
        return
    op.create_table(
        "whatsapp_chat_reads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("atendente_id", sa.Integer(), sa.ForeignKey("atendentes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chat_id", sa.Integer(), sa.ForeignKey("whatsapp_chats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("atendente_id", "chat_id", name="uq_whatsapp_chat_reads_atendente_chat"),
    )
    op.create_index(op.f("ix_whatsapp_chat_reads_atendente_id"), "whatsapp_chat_reads", ["atendente_id"], unique=False)
    op.create_index(op.f("ix_whatsapp_chat_reads_chat_id"), "whatsapp_chat_reads", ["chat_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_whatsapp_chat_reads_chat_id"), table_name="whatsapp_chat_reads")
    op.drop_index(op.f("ix_whatsapp_chat_reads_atendente_id"), table_name="whatsapp_chat_reads")
    op.drop_table("whatsapp_chat_reads")

