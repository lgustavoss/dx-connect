"""Janela de avaliação WhatsApp (~30 min) + templates timeout/pular.

Revision ID: 077_wpp_avaliacao_janela
Revises: 076_kb_portal_cor_sidebar
Create Date: 2026-07-21
"""

import sqlalchemy as sa
from alembic import op

revision = "077_wpp_avaliacao_janela"
down_revision = "076_kb_portal_cor_sidebar"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("whatsapp_settings"):
        return
    cols = {c["name"] for c in insp.get_columns("whatsapp_settings")}
    if "avaliacao_janela_minutos" not in cols:
        op.add_column(
            "whatsapp_settings",
            sa.Column("avaliacao_janela_minutos", sa.Integer(), nullable=False, server_default="30"),
        )
        op.alter_column("whatsapp_settings", "avaliacao_janela_minutos", server_default=None)
    if "auto_msg_avaliacao_timeout_texto" not in cols:
        op.add_column(
            "whatsapp_settings",
            sa.Column("auto_msg_avaliacao_timeout_texto", sa.Text(), nullable=True),
        )
    if "auto_msg_avaliacao_pular_texto" not in cols:
        op.add_column(
            "whatsapp_settings",
            sa.Column("auto_msg_avaliacao_pular_texto", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("whatsapp_settings"):
        return
    cols = {c["name"] for c in insp.get_columns("whatsapp_settings")}
    for col in (
        "auto_msg_avaliacao_pular_texto",
        "auto_msg_avaliacao_timeout_texto",
        "avaliacao_janela_minutos",
    ):
        if col in cols:
            op.drop_column("whatsapp_settings", col)
