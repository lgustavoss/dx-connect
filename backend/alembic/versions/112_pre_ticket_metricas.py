"""Migration 112 — métricas de análise IA pré-ticket (#815).

Revision ID: 112_pre_ticket_metricas
Revises: 111_pre_ticket_github
Create Date: 2026-08-22
"""

import sqlalchemy as sa
from alembic import op

revision = "112_pre_ticket_metricas"
down_revision = "111_pre_ticket_github"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("pre_ticket_analise_metricas"):
        return
    op.create_table(
        "pre_ticket_analise_metricas",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id",
            sa.Integer(),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "sessao_id",
            sa.Integer(),
            sa.ForeignKey("pre_ticket_sessoes.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "atendente_id",
            sa.Integer(),
            sa.ForeignKey("atendentes.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("sucesso", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("erro_tipo", sa.String(40), nullable=False, server_default="ok"),
        sa.Column("latencia_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("model", sa.String(80), nullable=True),
        sa.Column("prompt_version", sa.String(20), nullable=True),
        sa.Column("tokens_input", sa.Integer(), nullable=True),
        sa.Column("tokens_output", sa.Integer(), nullable=True),
        sa.Column("custo_estimado_usd", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("pre_ticket_analise_metricas"):
        op.drop_table("pre_ticket_analise_metricas")
