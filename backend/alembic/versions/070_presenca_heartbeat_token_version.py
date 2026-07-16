"""Presença via heartbeat no DB + token_version para forçar saída.

Revision ID: 070_presenca_token
Revises: 069_chat_interno_reply
Create Date: 2026-07-16

Online deixa de depender só do hub in-memory (quebra com Gunicorn N>1).
token_version invalida JWT ao forçar saída do atendente.
"""

import sqlalchemy as sa
from alembic import op

revision = "070_presenca_token"
down_revision = "069_chat_interno_reply"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("atendentes"):
        return
    cols = {c["name"] for c in insp.get_columns("atendentes")}
    if "presenca_online_desde" not in cols:
        op.add_column(
            "atendentes",
            sa.Column("presenca_online_desde", sa.DateTime(timezone=True), nullable=True),
        )
    if "presenca_heartbeat_em" not in cols:
        op.add_column(
            "atendentes",
            sa.Column("presenca_heartbeat_em", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(
            "ix_atendentes_presenca_heartbeat_em",
            "atendentes",
            ["presenca_heartbeat_em"],
        )
    if "token_version" not in cols:
        op.add_column(
            "atendentes",
            sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("atendentes"):
        return
    cols = {c["name"] for c in insp.get_columns("atendentes")}
    if "token_version" in cols:
        op.drop_column("atendentes", "token_version")
    if "presenca_heartbeat_em" in cols:
        op.drop_index("ix_atendentes_presenca_heartbeat_em", table_name="atendentes")
        op.drop_column("atendentes", "presenca_heartbeat_em")
    if "presenca_online_desde" in cols:
        op.drop_column("atendentes", "presenca_online_desde")
