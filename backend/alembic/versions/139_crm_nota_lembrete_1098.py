"""Notas do CRM: edição e lembrete de reunião (#1098).

Revision ID: 139_crm_nota_lembrete_1098
Revises: 138_saas_comentario_origem_1099
Create Date: 2026-09-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "139_crm_nota_lembrete_1098"
down_revision = "138_saas_comentario_origem_1099"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("crm_negociacao_atividades"):
        return
    cols = {c["name"] for c in insp.get_columns("crm_negociacao_atividades")}
    if "updated_at" not in cols:
        op.add_column(
            "crm_negociacao_atividades",
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "lembrete_em" not in cols:
        op.add_column(
            "crm_negociacao_atividades",
            sa.Column("lembrete_em", sa.DateTime(timezone=True), nullable=True),
        )
    if "lembrete_tentativa_em" not in cols:
        op.add_column(
            "crm_negociacao_atividades",
            sa.Column("lembrete_tentativa_em", sa.DateTime(timezone=True), nullable=True),
        )
    if "lembrete_disparado_em" not in cols:
        op.add_column(
            "crm_negociacao_atividades",
            sa.Column("lembrete_disparado_em", sa.DateTime(timezone=True), nullable=True),
        )
    indexes = {i["name"] for i in insp.get_indexes("crm_negociacao_atividades")}
    if "ix_crm_negociacao_atividades_lembrete_em" not in indexes:
        op.create_index(
            "ix_crm_negociacao_atividades_lembrete_em",
            "crm_negociacao_atividades",
            ["lembrete_em"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("crm_negociacao_atividades"):
        return
    indexes = {i["name"] for i in insp.get_indexes("crm_negociacao_atividades")}
    if "ix_crm_negociacao_atividades_lembrete_em" in indexes:
        op.drop_index(
            "ix_crm_negociacao_atividades_lembrete_em",
            table_name="crm_negociacao_atividades",
        )
    cols = {c["name"] for c in insp.get_columns("crm_negociacao_atividades")}
    if "lembrete_disparado_em" in cols:
        op.drop_column("crm_negociacao_atividades", "lembrete_disparado_em")
    if "lembrete_tentativa_em" in cols:
        op.drop_column("crm_negociacao_atividades", "lembrete_tentativa_em")
    if "lembrete_em" in cols:
        op.drop_column("crm_negociacao_atividades", "lembrete_em")
    if "updated_at" in cols:
        op.drop_column("crm_negociacao_atividades", "updated_at")
