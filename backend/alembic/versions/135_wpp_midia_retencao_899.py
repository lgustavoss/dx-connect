"""WhatsApp: retenção de mídia local + estado (#899/#900).

Revision ID: 135_wpp_midia_retencao_899
Revises: 134_ponto_dia_convocado_985
Create Date: 2026-09-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "135_wpp_midia_retencao_899"
down_revision = "134_ponto_dia_convocado_985"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    msg_cols = {c["name"] for c in insp.get_columns("whatsapp_mensagens")}
    if "midia_estado" not in msg_cols:
        op.add_column(
            "whatsapp_mensagens",
            sa.Column("midia_estado", sa.String(length=24), nullable=True),
        )
        op.create_index("ix_whatsapp_mensagens_midia_estado", "whatsapp_mensagens", ["midia_estado"])

    set_cols = {c["name"] for c in insp.get_columns("whatsapp_settings")}
    for name, default in (
        ("midia_retencao_dias_imagem", 90),
        ("midia_retencao_dias_audio", 90),
        ("midia_retencao_dias_video", 30),
        ("midia_retencao_dias_documento", 90),
    ):
        if name not in set_cols:
            op.add_column(
                "whatsapp_settings",
                sa.Column(name, sa.Integer(), nullable=False, server_default=str(default)),
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    set_cols = {c["name"] for c in insp.get_columns("whatsapp_settings")}
    for name in (
        "midia_retencao_dias_documento",
        "midia_retencao_dias_video",
        "midia_retencao_dias_audio",
        "midia_retencao_dias_imagem",
    ):
        if name in set_cols:
            op.drop_column("whatsapp_settings", name)
    msg_cols = {c["name"] for c in insp.get_columns("whatsapp_mensagens")}
    idxs = {i["name"] for i in insp.get_indexes("whatsapp_mensagens")}
    if "ix_whatsapp_mensagens_midia_estado" in idxs:
        op.drop_index("ix_whatsapp_mensagens_midia_estado", table_name="whatsapp_mensagens")
    if "midia_estado" in msg_cols:
        op.drop_column("whatsapp_mensagens", "midia_estado")
