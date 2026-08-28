"""Lote F: cobertura de plantão (#970).

Revision ID: 130_ponto_lote_f
Revises: 129_merge_he_teto_versao
Create Date: 2026-08-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "130_ponto_lote_f"
down_revision = "129_merge_he_teto_versao"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("ponto_coberturas"):
        return
    op.create_table(
        "ponto_coberturas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column(
            "solicitante_id",
            sa.Integer(),
            sa.ForeignKey("atendentes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "cobertor_id",
            sa.Integer(),
            sa.ForeignKey("atendentes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("data_ref", sa.Date(), nullable=False),
        sa.Column("motivo", sa.String(1000), nullable=True),
        sa.Column("estado", sa.String(32), nullable=False, server_default="pendente_cobertor"),
        sa.Column("origem", sa.String(20), nullable=False, server_default="solicitacao"),
        sa.Column("resposta_cobertor", sa.String(20), nullable=True),
        sa.Column("respondido_em", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_ponto_coberturas_tenant_id", "ponto_coberturas", ["tenant_id"])
    op.create_index("ix_ponto_coberturas_solicitante_id", "ponto_coberturas", ["solicitante_id"])
    op.create_index("ix_ponto_coberturas_cobertor_id", "ponto_coberturas", ["cobertor_id"])
    op.create_index("ix_ponto_coberturas_data_ref", "ponto_coberturas", ["data_ref"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("ponto_coberturas"):
        op.drop_table("ponto_coberturas")
