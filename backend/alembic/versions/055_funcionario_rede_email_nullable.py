"""funcionarios_rede.email opcional (#444).

Revision ID: 055_funcionario_rede_email_nullable
Revises: 054_kb_interno_only
Create Date: 2026-06-17
"""

import sqlalchemy as sa
from alembic import op

revision = "055_funcionario_rede_email_nullable"
down_revision = "054_kb_interno_only"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "funcionarios_rede",
        "email",
        existing_type=sa.String(length=255),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "funcionarios_rede",
        "email",
        existing_type=sa.String(length=255),
        nullable=False,
    )
