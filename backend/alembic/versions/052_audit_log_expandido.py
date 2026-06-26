"""Auditoria expandida: payload, IP, user-agent e request_id (#290).

Revision ID: 052_audit_log_expandido
Revises: 051_sla_policy_natureza
Create Date: 2026-06-24
"""

import sqlalchemy as sa
from alembic import op

revision = "052_audit_log_expandido"
down_revision = "051_sla_policy_natureza"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "audit_log",
        "action",
        existing_type=sa.String(length=20),
        type_=sa.String(length=40),
        existing_nullable=False,
    )
    op.add_column("audit_log", sa.Column("payload_json", sa.JSON(), nullable=True))
    op.add_column("audit_log", sa.Column("ip_address", sa.String(length=45), nullable=True))
    op.add_column("audit_log", sa.Column("user_agent", sa.String(length=512), nullable=True))
    op.add_column("audit_log", sa.Column("request_id", sa.String(length=64), nullable=True))
    op.create_index(op.f("ix_audit_log_request_id"), "audit_log", ["request_id"], unique=False)
    op.create_index(op.f("ix_audit_log_action"), "audit_log", ["action"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_log_action"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_request_id"), table_name="audit_log")
    op.drop_column("audit_log", "request_id")
    op.drop_column("audit_log", "user_agent")
    op.drop_column("audit_log", "ip_address")
    op.drop_column("audit_log", "payload_json")
    op.alter_column(
        "audit_log",
        "action",
        existing_type=sa.String(length=40),
        type_=sa.String(length=20),
        existing_nullable=False,
    )
