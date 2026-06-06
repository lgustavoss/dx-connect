"""tickets: rede_id para ticket de coordenação de rede.

Revision ID: 033_ticket_rede_id
Revises: 032_ticket_vinculos
Create Date: 2026-05-28
"""

from alembic import op
import sqlalchemy as sa

revision = "033_ticket_rede_id"
down_revision = "032_ticket_vinculos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("rede_id", sa.Integer(), nullable=True))
    op.create_index("ix_tickets_rede_id", "tickets", ["rede_id"], unique=False)
    op.create_foreign_key(
        "fk_tickets_rede_id_redes",
        "tickets",
        "redes",
        ["rede_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.execute(
        """
        UPDATE tickets t
        SET rede_id = e.rede_id
        FROM empresas e
        WHERE t.empresa_id = e.id AND t.rede_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_constraint("fk_tickets_rede_id_redes", "tickets", type_="foreignkey")
    op.drop_index("ix_tickets_rede_id", table_name="tickets")
    op.drop_column("tickets", "rede_id")
