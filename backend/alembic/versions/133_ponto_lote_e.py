"""Lote E: ausências programadas, pausa mínima, anexo justificativa (#976/#973/#977).

Revision ID: 133_ponto_lote_e
Revises: 132_ponto_he_teto_mensal
Create Date: 2026-08-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "133_ponto_lote_e"
down_revision = "132_ponto_he_teto_mensal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("ponto_ausencias"):
        op.create_table(
            "ponto_ausencias",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
            sa.Column(
                "atendente_id",
                sa.Integer(),
                sa.ForeignKey("atendentes.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("tipo", sa.String(32), nullable=False),
            sa.Column("desde", sa.Date(), nullable=False),
            sa.Column("ate", sa.Date(), nullable=False),
            sa.Column("motivo", sa.String(1000), nullable=True),
            sa.Column("estado", sa.String(20), nullable=False, server_default="pendente"),
            sa.Column("origem", sa.String(20), nullable=False, server_default="solicitacao"),
            sa.Column(
                "decidido_por_id",
                sa.Integer(),
                sa.ForeignKey("atendentes.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("decidido_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("decisao_motivo", sa.String(1000), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        )
        op.create_index("ix_ponto_ausencias_tenant_id", "ponto_ausencias", ["tenant_id"])
        op.create_index("ix_ponto_ausencias_atendente_id", "ponto_ausencias", ["atendente_id"])
        op.create_index("ix_ponto_ausencias_desde", "ponto_ausencias", ["desde"])
        op.create_index("ix_ponto_ausencias_ate", "ponto_ausencias", ["ate"])

    if insp.has_table("ponto_settings"):
        cols = {c["name"] for c in insp.get_columns("ponto_settings")}
        if "pausa_minima_minutos" not in cols:
            op.add_column(
                "ponto_settings",
                sa.Column("pausa_minima_minutos", sa.Integer(), nullable=False, server_default="0"),
            )

    if insp.has_table("ponto_justificativas"):
        cols = {c["name"] for c in insp.get_columns("ponto_justificativas")}
        if "anexo_nome" not in cols:
            op.add_column("ponto_justificativas", sa.Column("anexo_nome", sa.String(255), nullable=True))
        if "anexo_content_type" not in cols:
            op.add_column(
                "ponto_justificativas", sa.Column("anexo_content_type", sa.String(128), nullable=True)
            )
        if "anexo_storage_key" not in cols:
            op.add_column(
                "ponto_justificativas", sa.Column("anexo_storage_key", sa.String(255), nullable=True)
            )
        if "anexo_tamanho_bytes" not in cols:
            op.add_column(
                "ponto_justificativas", sa.Column("anexo_tamanho_bytes", sa.Integer(), nullable=True)
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("ponto_justificativas"):
        cols = {c["name"] for c in insp.get_columns("ponto_justificativas")}
        for col in ("anexo_tamanho_bytes", "anexo_storage_key", "anexo_content_type", "anexo_nome"):
            if col in cols:
                op.drop_column("ponto_justificativas", col)
    if insp.has_table("ponto_settings"):
        cols = {c["name"] for c in insp.get_columns("ponto_settings")}
        if "pausa_minima_minutos" in cols:
            op.drop_column("ponto_settings", "pausa_minima_minutos")
    if insp.has_table("ponto_ausencias"):
        op.drop_table("ponto_ausencias")
