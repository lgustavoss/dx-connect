"""Abono em solicitações de ajuste + campos nullable (#abono).

Revision ID: 142_ponto_abono
Revises: 141_ponto_he_politica
Create Date: 2026-09-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "142_ponto_abono"
down_revision = "141_ponto_he_politica"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("ponto_solicitacoes_ajuste"):
        return
    cols = {c["name"]: c for c in insp.get_columns("ponto_solicitacoes_ajuste")}
    if "tipo_batida" in cols and cols["tipo_batida"].get("nullable") is False:
        op.alter_column(
            "ponto_solicitacoes_ajuste",
            "tipo_batida",
            existing_type=sa.String(20),
            nullable=True,
        )
    if "horario_solicitado" in cols and cols["horario_solicitado"].get("nullable") is False:
        op.alter_column(
            "ponto_solicitacoes_ajuste",
            "horario_solicitado",
            existing_type=sa.DateTime(timezone=True),
            nullable=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("ponto_solicitacoes_ajuste"):
        return
    # Não reverte a nullable se já houver linhas abono (evita falha).
    cols = {c["name"] for c in insp.get_columns("ponto_solicitacoes_ajuste")}
    if "horario_solicitado" in cols:
        op.execute(
            "UPDATE ponto_solicitacoes_ajuste SET horario_solicitado = COALESCE(horario_solicitado, created_at) "
            "WHERE horario_solicitado IS NULL"
        )
        op.alter_column(
            "ponto_solicitacoes_ajuste",
            "horario_solicitado",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
        )
    if "tipo_batida" in cols:
        op.execute(
            "UPDATE ponto_solicitacoes_ajuste SET tipo_batida = COALESCE(tipo_batida, 'entrada') "
            "WHERE tipo_batida IS NULL"
        )
        op.alter_column(
            "ponto_solicitacoes_ajuste",
            "tipo_batida",
            existing_type=sa.String(20),
            nullable=False,
        )
