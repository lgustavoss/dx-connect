"""email_settings: envio transaccional via Resend (API HTTP).

Revision ID: 022_email_resend
Revises: 021_ticket_email_mid
Create Date: 2026-05-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "022_email_resend"
down_revision = "021_ticket_email_mid"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if not insp.has_table("email_settings"):
        return
    if not _has_column(insp, "email_settings", "transactional_api_key_enc"):
        op.add_column(
            "email_settings",
            sa.Column("transactional_api_key_enc", sa.String(length=2048), nullable=True),
        )
    if not _has_column(insp, "email_settings", "transactional_from_email"):
        op.add_column(
            "email_settings",
            sa.Column("transactional_from_email", sa.String(length=255), nullable=True),
        )
    if not _has_column(insp, "email_settings", "transactional_from_name"):
        op.add_column(
            "email_settings",
            sa.Column("transactional_from_name", sa.String(length=255), nullable=True),
        )


def _has_column(insp, table: str, col: str) -> bool:
    try:
        return any(c["name"] == col for c in insp.get_columns(table))
    except Exception:
        return False


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if not insp.has_table("email_settings"):
        return
    for col in ("transactional_from_name", "transactional_from_email", "transactional_api_key_enc"):
        if _has_column(insp, "email_settings", col):
            op.drop_column("email_settings", col)
