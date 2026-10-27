"""Token de instalação DeskRemote e credencial do computador.

Revision ID: 154_deskremote_enroll
Revises: 153_pdv_tipo_deskremote
Create Date: 2026-10-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "154_deskremote_enroll"
down_revision = "153_pdv_tipo_deskremote"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("empresa_pdv_acessos_remotos"):
        cols = {c["name"] for c in insp.get_columns("empresa_pdv_acessos_remotos")}
        if "senha_versao" not in cols:
            op.add_column(
                "empresa_pdv_acessos_remotos",
                sa.Column("senha_versao", sa.Integer(), nullable=False, server_default="1"),
            )

    if not insp.has_table("deskremote_install_tokens"):
        op.create_table(
            "deskremote_install_tokens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("pdv_id", sa.Integer(), sa.ForeignKey("empresa_pdvs.id", ondelete="CASCADE"), nullable=False),
            sa.Column(
                "acesso_id",
                sa.Integer(),
                sa.ForeignKey("empresa_pdv_acessos_remotos.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("token_hash", sa.String(64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_deskremote_install_tokens_pdv_id", "deskremote_install_tokens", ["pdv_id"])
        op.create_index("ix_deskremote_install_tokens_acesso_id", "deskremote_install_tokens", ["acesso_id"])
        op.create_index("ix_deskremote_install_tokens_token_hash", "deskremote_install_tokens", ["token_hash"], unique=True)

    if not insp.has_table("deskremote_dispositivos"):
        op.create_table(
            "deskremote_dispositivos",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("pdv_id", sa.Integer(), sa.ForeignKey("empresa_pdvs.id", ondelete="CASCADE"), nullable=False),
            sa.Column(
                "acesso_id",
                sa.Integer(),
                sa.ForeignKey("empresa_pdv_acessos_remotos.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("token_hash", sa.String(64), nullable=False),
            sa.Column("rustdesk_id", sa.String(64), nullable=True),
            sa.Column("senha_versao_aplicada", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_deskremote_dispositivos_pdv_id", "deskremote_dispositivos", ["pdv_id"])
        op.create_index("ix_deskremote_dispositivos_acesso_id", "deskremote_dispositivos", ["acesso_id"])
        op.create_index("ix_deskremote_dispositivos_token_hash", "deskremote_dispositivos", ["token_hash"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("deskremote_dispositivos"):
        op.drop_table("deskremote_dispositivos")
    if insp.has_table("deskremote_install_tokens"):
        op.drop_table("deskremote_install_tokens")
    if insp.has_table("empresa_pdv_acessos_remotos"):
        cols = {c["name"] for c in insp.get_columns("empresa_pdv_acessos_remotos")}
        if "senha_versao" in cols:
            op.drop_column("empresa_pdv_acessos_remotos", "senha_versao")
