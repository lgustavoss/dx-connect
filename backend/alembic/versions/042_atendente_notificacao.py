"""Preferências de notificação por atendente e fila de e-mail.

Revision ID: 042_atendente_notificacao
Revises: 041_ticket_csat
Create Date: 2026-06-12
"""

from alembic import op
import sqlalchemy as sa

revision = "042_atendente_notificacao"
down_revision = "041_ticket_csat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "atendente_notificacao_preferencias",
        sa.Column("atendente_id", sa.Integer(), nullable=False),
        sa.Column("email_habilitado", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("email_ticket_atribuido", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("email_nova_mensagem", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["atendente_id"], ["atendentes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("atendente_id"),
    )

    op.create_table(
        "notificacao_email_outbox",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("atendente_id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=True),
        sa.Column("tipo", sa.String(length=40), nullable=False),
        sa.Column("dedup_key", sa.String(length=120), nullable=False),
        sa.Column("to_email", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=998), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pendente"),
        sa.Column("tentativas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["atendente_id"], ["atendentes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notificacao_email_outbox_status_scheduled", "notificacao_email_outbox", ["status", "scheduled_at"])
    op.create_index("ix_notificacao_email_outbox_dedup_key", "notificacao_email_outbox", ["dedup_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_notificacao_email_outbox_dedup_key", table_name="notificacao_email_outbox")
    op.drop_index("ix_notificacao_email_outbox_status_scheduled", table_name="notificacao_email_outbox")
    op.drop_table("notificacao_email_outbox")
    op.drop_table("atendente_notificacao_preferencias")
