"""Tokens FCM do app companion (#1315).

Revision ID: 155_dispositivos_fcm
Revises: 154_deskremote_enroll
Create Date: 2026-10-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "155_dispositivos_fcm"
down_revision = "154_deskremote_enroll"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "dispositivos" not in tables:
        op.create_table(
            "dispositivos",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "atendente_id",
                sa.Integer(),
                sa.ForeignKey("atendentes.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("token", sa.String(length=512), nullable=False),
            sa.Column("plataforma", sa.String(length=32), nullable=False, server_default="android"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("token", name="uq_dispositivos_token"),
        )
        op.create_index("ix_dispositivos_atendente_id", "dispositivos", ["atendente_id"])

    if "fcm_outbox" not in tables:
        op.create_table(
            "fcm_outbox",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "atendente_id",
                sa.Integer(),
                sa.ForeignKey("atendentes.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("event_type", sa.String(length=64), nullable=False),
            sa.Column("dedup_key", sa.String(length=255), nullable=False),
            sa.Column("payload_json", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pendente"),
            sa.Column("tentativas", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("dedup_key", name="uq_fcm_outbox_dedup_key"),
        )
        op.create_index("ix_fcm_outbox_atendente_id", "fcm_outbox", ["atendente_id"])
        op.create_index("ix_fcm_outbox_event_type", "fcm_outbox", ["event_type"])
        op.create_index("ix_fcm_outbox_status", "fcm_outbox", ["status"])
        op.create_index("ix_fcm_outbox_scheduled_at", "fcm_outbox", ["scheduled_at"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    if "fcm_outbox" in tables:
        op.drop_table("fcm_outbox")
    if "dispositivos" in tables:
        op.drop_table("dispositivos")
