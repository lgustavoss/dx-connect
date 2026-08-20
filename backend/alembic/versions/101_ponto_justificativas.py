"""Ponto v3: justificativas (#774).

Revision ID: 101_ponto_justificativas
Revises: 100_ponto_pausas_ajustes
Create Date: 2026-08-20
"""

import sqlalchemy as sa
from alembic import op

revision = "101_ponto_justificativas"
down_revision = "100_ponto_pausas_ajustes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("ponto_justificativas"):
        return
    op.create_table(
        "ponto_justificativas",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id",
            sa.Integer(),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "atendente_id",
            sa.Integer(),
            sa.ForeignKey("atendentes.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("data_ref", sa.Date(), nullable=False, index=True),
        sa.Column("tipo", sa.String(32), nullable=False),
        sa.Column("motivo", sa.String(1000), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False, server_default="pendente"),
        sa.Column("decisao_motivo", sa.String(1000), nullable=True),
        sa.Column(
            "decidido_por_id",
            sa.Integer(),
            sa.ForeignKey("atendentes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("decidido_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )
    op.create_index(
        "ix_ponto_justificativas_estado_data",
        "ponto_justificativas",
        ["tenant_id", "estado", "data_ref"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("ponto_justificativas"):
        op.drop_index("ix_ponto_justificativas_estado_data", table_name="ponto_justificativas")
        op.drop_table("ponto_justificativas")
