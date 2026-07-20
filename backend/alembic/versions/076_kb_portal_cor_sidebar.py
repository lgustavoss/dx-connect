"""Cor do menu lateral no branding KB/portal.

Revision ID: 076_kb_portal_cor_sidebar
Revises: 075_portal_funcionario_auth
Create Date: 2026-07-20
"""

import sqlalchemy as sa
from alembic import op

revision = "076_kb_portal_cor_sidebar"
down_revision = "075_portal_funcionario_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("kb_portal_settings"):
        return
    cols = {c["name"] for c in insp.get_columns("kb_portal_settings")}
    if "cor_sidebar" not in cols:
        op.add_column(
            "kb_portal_settings",
            sa.Column("cor_sidebar", sa.String(7), nullable=True),
        )
        # Por padrão igual à navbar (cor_header) nas linhas existentes
        op.execute(
            sa.text(
                "UPDATE kb_portal_settings SET cor_sidebar = cor_header WHERE cor_sidebar IS NULL"
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("kb_portal_settings"):
        return
    cols = {c["name"] for c in insp.get_columns("kb_portal_settings")}
    if "cor_sidebar" in cols:
        op.drop_column("kb_portal_settings", "cor_sidebar")
