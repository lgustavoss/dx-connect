"""ticket_vinculos: relações duplicado_de / relacionado_a entre tickets.

Revision ID: 032_ticket_vinculos
Revises: 031_respostas_prontas
Create Date: 2026-05-28
"""

from alembic import op
import sqlalchemy as sa

revision = "032_ticket_vinculos"
down_revision = "031_respostas_prontas"
branch_labels = None
depends_on = None

TIPOS = ("duplicado_de", "relacionado_a")


def upgrade() -> None:
    op.create_table(
        "ticket_vinculos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("related_ticket_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["created_by_id"], ["atendentes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["related_ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_id", "related_ticket_id", "tipo", name="uq_ticket_vinculos_par_tipo"),
        sa.CheckConstraint("ticket_id <> related_ticket_id", name="ck_ticket_vinculos_distintos"),
    )
    op.create_index("ix_ticket_vinculos_tenant_id", "ticket_vinculos", ["tenant_id"], unique=False)
    op.create_index("ix_ticket_vinculos_ticket_id", "ticket_vinculos", ["ticket_id"], unique=False)
    op.create_index("ix_ticket_vinculos_related_ticket_id", "ticket_vinculos", ["related_ticket_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ticket_vinculos_related_ticket_id", table_name="ticket_vinculos")
    op.drop_index("ix_ticket_vinculos_ticket_id", table_name="ticket_vinculos")
    op.drop_index("ix_ticket_vinculos_tenant_id", table_name="ticket_vinculos")
    op.drop_table("ticket_vinculos")
