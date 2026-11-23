"""Pedido de atualização do DeskRemote pelo painel (#1436).

Revision ID: 166_deskremote_update_pedido
Revises: 165_deskremote_app_version
Create Date: 2026-11-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "166_deskremote_update_pedido"
down_revision = "165_deskremote_app_version"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("deskremote_dispositivos"):
        return
    cols = {c["name"] for c in insp.get_columns("deskremote_dispositivos")}
    if "update_solicitado_em" not in cols:
        op.add_column(
            "deskremote_dispositivos",
            sa.Column("update_solicitado_em", sa.DateTime(timezone=True), nullable=True),
        )
    if "update_status" not in cols:
        op.add_column(
            "deskremote_dispositivos",
            sa.Column("update_status", sa.String(length=32), nullable=True),
        )
    if "update_erro" not in cols:
        op.add_column(
            "deskremote_dispositivos",
            sa.Column("update_erro", sa.String(length=255), nullable=True),
        )
    if "update_solicitado_por_id" not in cols:
        op.add_column(
            "deskremote_dispositivos",
            sa.Column(
                "update_solicitado_por_id",
                sa.Integer(),
                sa.ForeignKey("atendentes.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("deskremote_dispositivos"):
        return
    cols = {c["name"] for c in insp.get_columns("deskremote_dispositivos")}
    for col in (
        "update_solicitado_por_id",
        "update_erro",
        "update_status",
        "update_solicitado_em",
    ):
        if col in cols:
            op.drop_column("deskremote_dispositivos", col)
