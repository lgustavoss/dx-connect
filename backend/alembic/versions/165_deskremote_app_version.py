"""Versão do app DeskRemote reportada pelo dispositivo (#1434).

Revision ID: 165_deskremote_app_version
Revises: 164_contrato_assinaturas
Create Date: 2026-11-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "165_deskremote_app_version"
down_revision = "164_contrato_assinaturas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("deskremote_dispositivos"):
        return
    cols = {c["name"] for c in insp.get_columns("deskremote_dispositivos")}
    if "app_version" not in cols:
        op.add_column(
            "deskremote_dispositivos",
            sa.Column("app_version", sa.String(length=32), nullable=True),
        )
    if "app_ui" not in cols:
        op.add_column(
            "deskremote_dispositivos",
            sa.Column("app_ui", sa.String(length=16), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("deskremote_dispositivos"):
        return
    cols = {c["name"] for c in insp.get_columns("deskremote_dispositivos")}
    if "app_ui" in cols:
        op.drop_column("deskremote_dispositivos", "app_ui")
    if "app_version" in cols:
        op.drop_column("deskremote_dispositivos", "app_version")
