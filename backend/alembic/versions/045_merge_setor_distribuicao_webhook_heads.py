<<<<<<<< HEAD:backend/alembic/versions/045_merge_setor_distribuicao_webhook_heads.py
"""Unifica heads: distribuição por setor + outbox webhook/e-mail retry.

Revision ID: 045_merge_setor_webhook
Revises: 043_setor_distribuicao, 044_webhook_outbox
Create Date: 2026-05-27
========
"""Unifica heads: distribuição por setor + webhook outbox.

Revision ID: 045_merge_setor_webhook
Revises: 043_setor_distribuicao, 044_webhook_outbox
Create Date: 2026-06-14
>>>>>>>> origin/main:backend/alembic/versions/045_merge_setor_webhook.py
"""

revision = "045_merge_setor_webhook"
down_revision = ("043_setor_distribuicao", "044_webhook_outbox")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
