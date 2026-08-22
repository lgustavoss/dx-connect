"""Pré-ticket IA — sessões de análise (#808 / #809).

Revision ID: 110_pre_ticket_ia
Revises: 109_ponto_geofence
Create Date: 2026-08-22
"""

import sqlalchemy as sa
from alembic import op

revision = "110_pre_ticket_ia"
down_revision = "109_ponto_geofence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("pre_ticket_sessoes"):
        return
    op.create_table(
        "pre_ticket_sessoes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id",
            sa.Integer(),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "ticket_id",
            sa.Integer(),
            sa.ForeignKey("tickets.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "criado_por_id",
            sa.Integer(),
            sa.ForeignKey("atendentes.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column("contexto", sa.Text(), nullable=False),
        sa.Column("problema", sa.Text(), nullable=False),
        sa.Column("impacto", sa.Text(), nullable=True),
        sa.Column("evidencias", sa.Text(), nullable=True),
        sa.Column("urgencia", sa.String(40), nullable=True),
        sa.Column("estado", sa.String(30), nullable=False, server_default="rascunho"),
        sa.Column("prompt_version", sa.String(20), nullable=True),
        sa.Column("analise_json", sa.Text(), nullable=True),
        sa.Column("rascunho_titulo", sa.String(255), nullable=True),
        sa.Column("rascunho_corpo", sa.Text(), nullable=True),
        sa.Column("github_repo", sa.String(120), nullable=True),
        sa.Column("github_issue_number", sa.Integer(), nullable=True),
        sa.Column("github_issue_url", sa.String(500), nullable=True),
        sa.Column(
            "aprovado_por_id",
            sa.Integer(),
            sa.ForeignKey("atendentes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("aprovado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("publicado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("pre_ticket_sessoes"):
        op.drop_table("pre_ticket_sessoes")
