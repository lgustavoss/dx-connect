"""Migration 111 — publicação GitHub + histórico pré-ticket (#813 / #814).

Revision ID: 111_pre_ticket_github
Revises: 110_pre_ticket_ia
Create Date: 2026-08-22
"""

import sqlalchemy as sa
from alembic import op

revision = "111_pre_ticket_github"
down_revision = "110_pre_ticket_ia"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("pre_ticket_sessoes"):
        cols = {c["name"] for c in insp.get_columns("pre_ticket_sessoes")}
        if "publicado_por_id" not in cols:
            op.add_column(
                "pre_ticket_sessoes",
                sa.Column(
                    "publicado_por_id",
                    sa.Integer(),
                    sa.ForeignKey("atendentes.id", ondelete="SET NULL"),
                    nullable=True,
                ),
            )
        if "rascunho_publicado_titulo" not in cols:
            op.add_column(
                "pre_ticket_sessoes",
                sa.Column("rascunho_publicado_titulo", sa.String(255), nullable=True),
            )
        if "rascunho_publicado_corpo" not in cols:
            op.add_column(
                "pre_ticket_sessoes",
                sa.Column("rascunho_publicado_corpo", sa.Text(), nullable=True),
            )
        if "github_last_error" not in cols:
            op.add_column(
                "pre_ticket_sessoes",
                sa.Column("github_last_error", sa.Text(), nullable=True),
            )

    if not insp.has_table("pre_ticket_historico"):
        op.create_table(
            "pre_ticket_historico",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "sessao_id",
                sa.Integer(),
                sa.ForeignKey("pre_ticket_sessoes.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("acao", sa.String(40), nullable=False),
            sa.Column("detalhe", sa.Text(), nullable=True),
            sa.Column(
                "atendente_id",
                sa.Integer(),
                sa.ForeignKey("atendentes.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("atendente_nome", sa.String(255), nullable=True),
            sa.Column("payload_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("pre_ticket_historico"):
        op.drop_table("pre_ticket_historico")
    if insp.has_table("pre_ticket_sessoes"):
        cols = {c["name"] for c in insp.get_columns("pre_ticket_sessoes")}
        for name in (
            "github_last_error",
            "rascunho_publicado_corpo",
            "rascunho_publicado_titulo",
            "publicado_por_id",
        ):
            if name in cols:
                op.drop_column("pre_ticket_sessoes", name)
