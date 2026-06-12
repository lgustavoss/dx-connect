"""Tickets: CSAT por e-mail (convite + avaliação do cliente).

Revision ID: 041_ticket_csat
Revises: 040_wpp_chat_funcionario
Create Date: 2026-06-11
"""

from alembic import op
import sqlalchemy as sa

revision = "041_ticket_csat"
down_revision = "040_wpp_chat_funcionario"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ticket_csat_invites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("atendente_id", sa.Integer(), nullable=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["atendente_id"], ["atendentes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ticket_csat_invites_ticket_id", "ticket_csat_invites", ["ticket_id"])
    op.create_index("ix_ticket_csat_invites_token_hash", "ticket_csat_invites", ["token_hash"], unique=True)

    op.create_table(
        "ticket_avaliacoes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("atendente_id", sa.Integer(), nullable=True),
        sa.Column("nota", sa.Integer(), nullable=False),
        sa.Column("comentario", sa.Text(), nullable=True),
        sa.Column("respondida_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("invite_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["atendente_id"], ["atendentes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["invite_id"], ["ticket_csat_invites.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_id", name="uq_ticket_avaliacoes_ticket_id"),
    )
    op.create_index("ix_ticket_avaliacoes_atendente_id", "ticket_avaliacoes", ["atendente_id"])


def downgrade() -> None:
    op.drop_index("ix_ticket_avaliacoes_atendente_id", table_name="ticket_avaliacoes")
    op.drop_table("ticket_avaliacoes")
    op.drop_index("ix_ticket_csat_invites_token_hash", table_name="ticket_csat_invites")
    op.drop_index("ix_ticket_csat_invites_ticket_id", table_name="ticket_csat_invites")
    op.drop_table("ticket_csat_invites")
