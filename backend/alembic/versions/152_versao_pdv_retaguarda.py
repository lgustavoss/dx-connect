"""Versão do PDV na empresa e do retaguarda na rede.

Revision ID: 152_versao_pdv_retaguarda
Revises: 151_pdv_acessos_remotos
Create Date: 2026-10-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "152_versao_pdv_retaguarda"
down_revision = "151_pdv_acessos_remotos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    emp_cols = {c["name"] for c in insp.get_columns("empresas")} if insp.has_table("empresas") else set()
    if "versao_pdv" not in emp_cols:
        op.add_column("empresas", sa.Column("versao_pdv", sa.String(length=80), nullable=True))
    rede_cols = {c["name"] for c in insp.get_columns("redes")} if insp.has_table("redes") else set()
    if "versao_retaguarda" not in rede_cols:
        op.add_column("redes", sa.Column("versao_retaguarda", sa.String(length=80), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    emp_cols = {c["name"] for c in insp.get_columns("empresas")} if insp.has_table("empresas") else set()
    if "versao_pdv" in emp_cols:
        op.drop_column("empresas", "versao_pdv")
    rede_cols = {c["name"] for c in insp.get_columns("redes")} if insp.has_table("redes") else set()
    if "versao_retaguarda" in rede_cols:
        op.drop_column("redes", "versao_retaguarda")
