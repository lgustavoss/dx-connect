"""SLA: preferências de alerta e registro de emissões (#279).

Revision ID: 048_sla_alertas
Revises: 047_sla_policies
Create Date: 2026-06-23
"""

import sqlalchemy as sa
from alembic import op

revision = "048_sla_alertas"
down_revision = "047_sla_policies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "atendente_notificacao_preferencias",
        sa.Column("email_sla_em_risco", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "atendente_notificacao_preferencias",
        sa.Column("email_sla_violado", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.alter_column("atendente_notificacao_preferencias", "email_sla_em_risco", server_default=None)
    op.alter_column("atendente_notificacao_preferencias", "email_sla_violado", server_default=None)

    op.create_table(
        "sla_alerta_emitidos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("meta", sa.String(length=30), nullable=False),
        sa.Column("evento", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_id", "meta", "evento", name="uq_sla_alerta_emitidos_ticket_meta_evento"),
    )
    op.create_index(op.f("ix_sla_alerta_emitidos_id"), "sla_alerta_emitidos", ["id"], unique=False)
    op.create_index(op.f("ix_sla_alerta_emitidos_ticket_id"), "sla_alerta_emitidos", ["ticket_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sla_alerta_emitidos_ticket_id"), table_name="sla_alerta_emitidos")
    op.drop_index(op.f("ix_sla_alerta_emitidos_id"), table_name="sla_alerta_emitidos")
    op.drop_table("sla_alerta_emitidos")
    op.drop_column("atendente_notificacao_preferencias", "email_sla_violado")
    op.drop_column("atendente_notificacao_preferencias", "email_sla_em_risco")
