"""Sistema: logo da empresa_sistema.

Revision ID: 018_sys_logo
Revises: 017_sys_email
Create Date: 2026-04-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "018_sys_logo"
down_revision = "017_sys_email"
branch_labels = None
depends_on = None


def _has_column(insp, table: str, column: str) -> bool:
    try:
        cols = insp.get_columns(table)
    except Exception:
        return False
    return any(c.get("name") == column for c in cols)


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if not insp.has_table("empresa_sistema"):
        return

    if not _has_column(insp, "empresa_sistema", "logo_filename"):
        op.add_column("empresa_sistema", sa.Column("logo_filename", sa.String(length=255), nullable=True))
    if not _has_column(insp, "empresa_sistema", "logo_mimetype"):
        op.add_column("empresa_sistema", sa.Column("logo_mimetype", sa.String(length=100), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if not insp.has_table("empresa_sistema"):
        return
    if _has_column(insp, "empresa_sistema", "logo_mimetype"):
        op.drop_column("empresa_sistema", "logo_mimetype")
    if _has_column(insp, "empresa_sistema", "logo_filename"):
        op.drop_column("empresa_sistema", "logo_filename")

