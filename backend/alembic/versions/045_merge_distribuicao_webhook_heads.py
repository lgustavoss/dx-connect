"""Unifica heads: distribuicao tickets + webhook outbox.

Revision ID: 045_merge_distrib_webhook
Revises: 043_setor_distribuicao, 044_webhook_outbox
Create Date: 2026-06-17
"""

revision = "045_merge_distrib_webhook"
down_revision = ("043_setor_distribuicao", "044_webhook_outbox")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
