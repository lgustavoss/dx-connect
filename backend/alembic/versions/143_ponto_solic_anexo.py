"""Anexo opcional em solicitações de ajuste de ponto.

Revision ID: 143_ponto_solic_anexo
Revises: 142_ponto_abono
Create Date: 2026-09-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "143_ponto_solic_anexo"
down_revision = "142_ponto_abono"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("ponto_solicitacoes_ajuste"):
        return
    cols = {c["name"] for c in insp.get_columns("ponto_solicitacoes_ajuste")}
    if "anexo_storage_key" not in cols:
        op.add_column(
            "ponto_solicitacoes_ajuste",
            sa.Column("anexo_storage_key", sa.String(255), nullable=True),
        )
    if "anexo_nome" not in cols:
        op.add_column(
            "ponto_solicitacoes_ajuste",
            sa.Column("anexo_nome", sa.String(255), nullable=True),
        )
    if "anexo_content_type" not in cols:
        op.add_column(
            "ponto_solicitacoes_ajuste",
            sa.Column("anexo_content_type", sa.String(128), nullable=True),
        )
    if "anexo_tamanho_bytes" not in cols:
        op.add_column(
            "ponto_solicitacoes_ajuste",
            sa.Column("anexo_tamanho_bytes", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("ponto_solicitacoes_ajuste"):
        return
    cols = {c["name"] for c in insp.get_columns("ponto_solicitacoes_ajuste")}
    for name in (
        "anexo_tamanho_bytes",
        "anexo_content_type",
        "anexo_nome",
        "anexo_storage_key",
    ):
        if name in cols:
            op.drop_column("ponto_solicitacoes_ajuste", name)
