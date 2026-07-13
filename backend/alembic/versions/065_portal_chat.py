"""KB portal: chat ao vivo visitante ↔ atendente (#468).

Revision ID: 065_portal_chat
Revises: 064_kb_article_feedback
Create Date: 2026-07-11
"""

import sqlalchemy as sa
from alembic import op

revision = "065_portal_chat"
down_revision = "064_kb_article_feedback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "kb_portal_settings",
        sa.Column("chat_habilitado", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "kb_portal_settings",
        sa.Column("chat_setor_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "kb_portal_settings",
        sa.Column("chat_texto_boas_vindas", sa.String(length=500), nullable=True),
    )
    op.create_foreign_key(
        "fk_kb_portal_settings_chat_setor_id",
        "kb_portal_settings",
        "setores",
        ["chat_setor_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "portal_chats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("protocolo", sa.String(length=32), nullable=False),
        sa.Column("visitor_token_hash", sa.String(length=64), nullable=False),
        sa.Column("visitante_nome", sa.String(length=120), nullable=False),
        sa.Column("visitante_email", sa.String(length=255), nullable=True),
        sa.Column("estado", sa.String(length=40), nullable=False),
        sa.Column("setor_id", sa.Integer(), nullable=True),
        sa.Column("atendente_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("atendimento_inicio_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("encerramento_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["atendente_id"], ["atendentes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["setor_id"], ["setores.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("protocolo"),
        sa.UniqueConstraint("visitor_token_hash", name="uq_portal_chats_visitor_token_hash"),
    )
    op.create_index("ix_portal_chats_tenant_id", "portal_chats", ["tenant_id"])
    op.create_index("ix_portal_chats_estado", "portal_chats", ["estado"])
    op.create_index("ix_portal_chats_setor_id", "portal_chats", ["setor_id"])
    op.create_index("ix_portal_chats_atendente_id", "portal_chats", ["atendente_id"])

    op.create_table(
        "portal_mensagens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chat_id", sa.Integer(), nullable=False),
        sa.Column("direcao", sa.String(length=16), nullable=False),
        sa.Column("corpo", sa.Text(), nullable=False),
        sa.Column("atendente_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["atendente_id"], ["atendentes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["chat_id"], ["portal_chats.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_portal_mensagens_chat_id", "portal_mensagens", ["chat_id"])

    op.create_table(
        "portal_chat_reads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chat_id", sa.Integer(), nullable=False),
        sa.Column("atendente_id", sa.Integer(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["atendente_id"], ["atendentes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chat_id"], ["portal_chats.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chat_id", "atendente_id", name="uq_portal_chat_reads_chat_atendente"),
    )
    op.create_index("ix_portal_chat_reads_chat_id", "portal_chat_reads", ["chat_id"])
    op.create_index("ix_portal_chat_reads_atendente_id", "portal_chat_reads", ["atendente_id"])


def downgrade() -> None:
    op.drop_table("portal_chat_reads")
    op.drop_table("portal_mensagens")
    op.drop_table("portal_chats")
    op.drop_constraint("fk_kb_portal_settings_chat_setor_id", "kb_portal_settings", type_="foreignkey")
    op.drop_column("kb_portal_settings", "chat_texto_boas_vindas")
    op.drop_column("kb_portal_settings", "chat_setor_id")
    op.drop_column("kb_portal_settings", "chat_habilitado")
