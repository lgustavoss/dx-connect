"""Vários acessos remotos por PDV.

Revision ID: 151_pdv_acessos_remotos
Revises: 150_pdv_tipo_deskrudder
Create Date: 2026-10-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "151_pdv_acessos_remotos"
down_revision = "150_pdv_tipo_deskrudder"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("empresa_pdvs"):
        return
    if not insp.has_table("empresa_pdv_acessos_remotos"):
        op.create_table(
            "empresa_pdv_acessos_remotos",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "pdv_id",
                sa.Integer(),
                sa.ForeignKey("empresa_pdvs.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("tipo_acesso_remoto_id", sa.Integer(), sa.ForeignKey("pdv_tipos_acesso_remoto.id"), nullable=True),
            sa.Column("acesso_remoto_id", sa.String(255), nullable=True),
            sa.Column("acesso_remoto_senha_cifrada", sa.Text(), nullable=True),
            sa.Column("ordem_exibicao", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_empresa_pdv_acessos_pdv_id", "empresa_pdv_acessos_remotos", ["pdv_id"])
    op.execute(
        sa.text(
            """
            INSERT INTO empresa_pdv_acessos_remotos (
                pdv_id, tipo_acesso_remoto_id, acesso_remoto_id, acesso_remoto_senha_cifrada, ordem_exibicao
            )
            SELECT p.id, p.tipo_acesso_remoto_id, p.acesso_remoto_id, p.acesso_remoto_senha_cifrada, 0
            FROM empresa_pdvs AS p
            WHERE (
                p.tipo_acesso_remoto_id IS NOT NULL
                OR p.acesso_remoto_id IS NOT NULL
                OR p.acesso_remoto_senha_cifrada IS NOT NULL
            )
            AND NOT EXISTS (
                SELECT 1 FROM empresa_pdv_acessos_remotos AS a WHERE a.pdv_id = p.id
            )
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("empresa_pdv_acessos_remotos"):
        op.drop_index("ix_empresa_pdv_acessos_pdv_id", table_name="empresa_pdv_acessos_remotos")
        op.drop_table("empresa_pdv_acessos_remotos")
