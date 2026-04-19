"""whatsapp integration

Revision ID: 005_whatsapp
Revises: 004_must_pwd
Create Date: 2026-04-19
"""

from alembic import op
import sqlalchemy as sa

revision = "005_whatsapp"
down_revision = "004_must_pwd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "whatsapp_conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("wa_id", sa.String(length=32), nullable=False),
        sa.Column("profile_name", sa.String(length=255), nullable=True),
        sa.Column("phone_number", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="open"),
        sa.Column("ai_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ai_mode", sa.String(length=20), nullable=False, server_default="assist"),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("linked_ticket_id", sa.Integer(), sa.ForeignKey("tickets.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_whatsapp_conversations_wa_id", "whatsapp_conversations", ["wa_id"], unique=True)
    op.create_index("ix_whatsapp_conversations_id", "whatsapp_conversations", ["id"], unique=False)
    op.create_index("ix_whatsapp_conversations_linked_ticket_id", "whatsapp_conversations", ["linked_ticket_id"], unique=False)

    op.create_table(
        "whatsapp_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("whatsapp_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ticket_id", sa.Integer(), sa.ForeignKey("tickets.id"), nullable=True),
        sa.Column("wa_message_id", sa.String(length=255), nullable=True),
        sa.Column("direction", sa.String(length=20), nullable=False),
        sa.Column("sender_phone", sa.String(length=32), nullable=True),
        sa.Column("recipient_phone", sa.String(length=32), nullable=True),
        sa.Column("message_type", sa.String(length=30), nullable=False, server_default="text"),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("media_url", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_whatsapp_messages_id", "whatsapp_messages", ["id"], unique=False)
    op.create_index("ix_whatsapp_messages_conversation_id", "whatsapp_messages", ["conversation_id"], unique=False)
    op.create_index("ix_whatsapp_messages_ticket_id", "whatsapp_messages", ["ticket_id"], unique=False)
    op.create_index("ix_whatsapp_messages_wa_message_id", "whatsapp_messages", ["wa_message_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_whatsapp_messages_wa_message_id", table_name="whatsapp_messages")
    op.drop_index("ix_whatsapp_messages_ticket_id", table_name="whatsapp_messages")
    op.drop_index("ix_whatsapp_messages_conversation_id", table_name="whatsapp_messages")
    op.drop_index("ix_whatsapp_messages_id", table_name="whatsapp_messages")
    op.drop_table("whatsapp_messages")

    op.drop_index("ix_whatsapp_conversations_linked_ticket_id", table_name="whatsapp_conversations")
    op.drop_index("ix_whatsapp_conversations_id", table_name="whatsapp_conversations")
    op.drop_index("ix_whatsapp_conversations_wa_id", table_name="whatsapp_conversations")
    op.drop_table("whatsapp_conversations")
