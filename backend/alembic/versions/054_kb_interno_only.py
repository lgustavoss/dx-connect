"""KB: flag interno_only em artigos (#295).

Revision ID: 054_kb_interno_only
Revises: 053_kb_categories_articles
Create Date: 2026-06-17
"""

import sqlalchemy as sa
from alembic import op

revision = "054_kb_interno_only"
down_revision = "053_kb_categories_articles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "kb_articles",
        sa.Column("interno_only", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("kb_articles", "interno_only")
