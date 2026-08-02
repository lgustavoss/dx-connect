"""WhatsApp: foto de perfil do contacto (URL em cache).

Revision ID: 078_wpp_foto_perfil
Revises: 077_wpp_avaliacao_janela
Create Date: 2026-08-01
"""

import sqlalchemy as sa
from alembic import op

revision = "078_wpp_foto_perfil"
down_revision = "077_wpp_avaliacao_janela"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("whatsapp_chats"):
        return
    cols = {c["name"] for c in insp.get_columns("whatsapp_chats")}
    if "foto_perfil_url" not in cols:
        op.add_column("whatsapp_chats", sa.Column("foto_perfil_url", sa.Text(), nullable=True))
    if "foto_perfil_atualizada_em" not in cols:
        op.add_column(
            "whatsapp_chats",
            sa.Column("foto_perfil_atualizada_em", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("whatsapp_chats"):
        return
    cols = {c["name"] for c in insp.get_columns("whatsapp_chats")}
    if "foto_perfil_atualizada_em" in cols:
        op.drop_column("whatsapp_chats", "foto_perfil_atualizada_em")
    if "foto_perfil_url" in cols:
        op.drop_column("whatsapp_chats", "foto_perfil_url")
