"""WhatsApp Evolution: settings, chats, mensagens, vínculos tickets.

Revision ID: 007_whatsapp_evolution
Revises: 006_ticket_reads
Create Date: 2026-04-20
"""

from alembic import op
import sqlalchemy as sa


revision = "007_whatsapp_evolution"
down_revision = "006_ticket_reads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "whatsapp_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("evolution_base_url", sa.String(length=500), nullable=True),
        sa.Column("evolution_instance_name", sa.String(length=120), nullable=True),
        sa.Column("evolution_api_key", sa.String(length=500), nullable=True),
        sa.Column("webhook_secret", sa.String(length=255), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_whatsapp_settings_id"), "whatsapp_settings", ["id"], unique=False)

    op.create_table(
        "whatsapp_chats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("protocolo", sa.String(length=32), nullable=False),
        sa.Column("wa_id", sa.String(length=64), nullable=False),
        sa.Column("cliente_nome", sa.String(length=255), nullable=True),
        sa.Column("estado", sa.String(length=40), nullable=False),
        sa.Column("atendente_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("atendimento_inicio_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("encerramento_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["atendente_id"], ["atendentes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("protocolo"),
    )
    op.create_index(op.f("ix_whatsapp_chats_id"), "whatsapp_chats", ["id"], unique=False)
    op.create_index(op.f("ix_whatsapp_chats_protocolo"), "whatsapp_chats", ["protocolo"], unique=True)
    op.create_index(op.f("ix_whatsapp_chats_wa_id"), "whatsapp_chats", ["wa_id"], unique=False)
    op.create_index(op.f("ix_whatsapp_chats_estado"), "whatsapp_chats", ["estado"], unique=False)
    op.create_index(op.f("ix_whatsapp_chats_atendente_id"), "whatsapp_chats", ["atendente_id"], unique=False)

    op.create_table(
        "whatsapp_mensagens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chat_id", sa.Integer(), nullable=False),
        sa.Column("direcao", sa.String(length=20), nullable=False),
        sa.Column("corpo", sa.Text(), nullable=False),
        sa.Column("wa_message_id", sa.String(length=128), nullable=True),
        sa.Column("atendente_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["atendente_id"], ["atendentes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["chat_id"], ["whatsapp_chats.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("wa_message_id", name="uq_whatsapp_mensagens_wa_message_id"),
    )
    op.create_index(op.f("ix_whatsapp_mensagens_id"), "whatsapp_mensagens", ["id"], unique=False)
    op.create_index(op.f("ix_whatsapp_mensagens_chat_id"), "whatsapp_mensagens", ["chat_id"], unique=False)
    op.create_index(op.f("ix_whatsapp_mensagens_wa_message_id"), "whatsapp_mensagens", ["wa_message_id"], unique=False)

    op.create_table(
        "whatsapp_chat_tickets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chat_id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("atendente_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["atendente_id"], ["atendentes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["chat_id"], ["whatsapp_chats.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chat_id", "ticket_id", name="uq_whatsapp_chat_ticket_par"),
    )
    op.create_index(op.f("ix_whatsapp_chat_tickets_id"), "whatsapp_chat_tickets", ["id"], unique=False)
    op.create_index(op.f("ix_whatsapp_chat_tickets_chat_id"), "whatsapp_chat_tickets", ["chat_id"], unique=False)
    op.create_index(op.f("ix_whatsapp_chat_tickets_ticket_id"), "whatsapp_chat_tickets", ["ticket_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_whatsapp_chat_tickets_ticket_id"), table_name="whatsapp_chat_tickets")
    op.drop_index(op.f("ix_whatsapp_chat_tickets_chat_id"), table_name="whatsapp_chat_tickets")
    op.drop_index(op.f("ix_whatsapp_chat_tickets_id"), table_name="whatsapp_chat_tickets")
    op.drop_table("whatsapp_chat_tickets")
    op.drop_index(op.f("ix_whatsapp_mensagens_wa_message_id"), table_name="whatsapp_mensagens")
    op.drop_index(op.f("ix_whatsapp_mensagens_chat_id"), table_name="whatsapp_mensagens")
    op.drop_index(op.f("ix_whatsapp_mensagens_id"), table_name="whatsapp_mensagens")
    op.drop_table("whatsapp_mensagens")
    op.drop_index(op.f("ix_whatsapp_chats_atendente_id"), table_name="whatsapp_chats")
    op.drop_index(op.f("ix_whatsapp_chats_estado"), table_name="whatsapp_chats")
    op.drop_index(op.f("ix_whatsapp_chats_wa_id"), table_name="whatsapp_chats")
    op.drop_index(op.f("ix_whatsapp_chats_protocolo"), table_name="whatsapp_chats")
    op.drop_index(op.f("ix_whatsapp_chats_id"), table_name="whatsapp_chats")
    op.drop_table("whatsapp_chats")
    op.drop_index(op.f("ix_whatsapp_settings_id"), table_name="whatsapp_settings")
    op.drop_table("whatsapp_settings")
