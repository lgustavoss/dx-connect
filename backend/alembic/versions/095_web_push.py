"""Web Push: subscriptions, outbox e preferências (#693 / #694).

Revision ID: 095_web_push
Revises: 094_wpp_midia_nome_original
Create Date: 2026-08-18
"""

import sqlalchemy as sa
from alembic import op

revision = "095_web_push"
down_revision = "094_wpp_midia_nome_original"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "push_subscription" not in tables:
        op.create_table(
            "push_subscription",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("atendente_id", sa.Integer(), sa.ForeignKey("atendentes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("endpoint", sa.String(length=2048), nullable=False),
            sa.Column("p256dh", sa.String(length=255), nullable=False),
            sa.Column("auth", sa.String(length=255), nullable=False),
            sa.Column("user_agent", sa.String(length=512), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("endpoint", name="uq_push_subscription_endpoint"),
        )
        op.create_index("ix_push_subscription_atendente_id", "push_subscription", ["atendente_id"])

    if "push_outbox" not in tables:
        op.create_table(
            "push_outbox",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("atendente_id", sa.Integer(), sa.ForeignKey("atendentes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("event_type", sa.String(length=64), nullable=False),
            sa.Column("dedup_key", sa.String(length=255), nullable=False),
            sa.Column("payload_json", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pendente"),
            sa.Column("tentativas", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("dedup_key", name="uq_push_outbox_dedup_key"),
        )
        op.create_index("ix_push_outbox_atendente_id", "push_outbox", ["atendente_id"])
        op.create_index("ix_push_outbox_event_type", "push_outbox", ["event_type"])
        op.create_index("ix_push_outbox_status", "push_outbox", ["status"])
        op.create_index("ix_push_outbox_scheduled_at", "push_outbox", ["scheduled_at"])

    prefs_cols = {c["name"] for c in insp.get_columns("atendente_notificacao_preferencias")}
    if "push_habilitado" not in prefs_cols:
        op.add_column(
            "atendente_notificacao_preferencias",
            sa.Column("push_habilitado", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )
    if "push_fila" not in prefs_cols:
        op.add_column(
            "atendente_notificacao_preferencias",
            sa.Column("push_fila", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    prefs_cols = {c["name"] for c in insp.get_columns("atendente_notificacao_preferencias")}
    if "push_fila" in prefs_cols:
        op.drop_column("atendente_notificacao_preferencias", "push_fila")
    if "push_habilitado" in prefs_cols:
        op.drop_column("atendente_notificacao_preferencias", "push_habilitado")
    tables = set(insp.get_table_names())
    if "push_outbox" in tables:
        op.drop_table("push_outbox")
    if "push_subscription" in tables:
        op.drop_table("push_subscription")
