"""Solicitações de inclusão/correção de batida (#1135).

Revision ID: 140_ponto_solic_ajuste_1135
Revises: 139_crm_nota_lembrete_1098
Create Date: 2026-09-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "140_ponto_solic_ajuste_1135"
down_revision = "139_crm_nota_lembrete_1098"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("ponto_solicitacoes_ajuste"):
        return
    op.create_table(
        "ponto_solicitacoes_ajuste",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column(
            "atendente_id",
            sa.Integer(),
            sa.ForeignKey("atendentes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False, server_default="pendente"),
        sa.Column("motivo", sa.String(1000), nullable=False),
        sa.Column("data_ref", sa.Date(), nullable=False),
        sa.Column("tipo_batida", sa.String(20), nullable=False),
        sa.Column("horario_solicitado", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "batida_id",
            sa.Integer(),
            sa.ForeignKey("ponto_batidas.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("decisao_motivo", sa.String(1000), nullable=True),
        sa.Column(
            "decidido_por_id",
            sa.Integer(),
            sa.ForeignKey("atendentes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("decidido_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_ponto_solicitacoes_ajuste_tenant_id", "ponto_solicitacoes_ajuste", ["tenant_id"])
    op.create_index("ix_ponto_solicitacoes_ajuste_atendente_id", "ponto_solicitacoes_ajuste", ["atendente_id"])
    op.create_index("ix_ponto_solicitacoes_ajuste_data_ref", "ponto_solicitacoes_ajuste", ["data_ref"])
    op.create_index("ix_ponto_solicitacoes_ajuste_batida_id", "ponto_solicitacoes_ajuste", ["batida_id"])
    op.create_index("ix_ponto_solicitacoes_ajuste_estado", "ponto_solicitacoes_ajuste", ["estado"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("ponto_solicitacoes_ajuste"):
        return
    op.drop_index("ix_ponto_solicitacoes_ajuste_estado", table_name="ponto_solicitacoes_ajuste")
    op.drop_index("ix_ponto_solicitacoes_ajuste_batida_id", table_name="ponto_solicitacoes_ajuste")
    op.drop_index("ix_ponto_solicitacoes_ajuste_data_ref", table_name="ponto_solicitacoes_ajuste")
    op.drop_index("ix_ponto_solicitacoes_ajuste_atendente_id", table_name="ponto_solicitacoes_ajuste")
    op.drop_index("ix_ponto_solicitacoes_ajuste_tenant_id", table_name="ponto_solicitacoes_ajuste")
    op.drop_table("ponto_solicitacoes_ajuste")
