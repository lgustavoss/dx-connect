"""Rede: adicionar login_retaguarda.

Revision ID: 005_rede_login_retaguarda
Revises: 004_must_pwd
Create Date: 2026-04-14
"""

from alembic import op
import sqlalchemy as sa


revision = "005_rede_login_retaguarda"
down_revision = "004_must_pwd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("redes", sa.Column("login_retaguarda", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("redes", "login_retaguarda")

