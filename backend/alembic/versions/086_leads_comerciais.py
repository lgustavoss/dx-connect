"""Tabela leads_comerciais — canal B2B da landing (DR-06).

Revision ID: 086_leads_comerciais
Revises: 085_saas_fase3
Create Date: 2026-07-23
"""

import sqlalchemy as sa
from alembic import op

revision = "086_leads_comerciais"
down_revision = "085_saas_fase3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("leads_comerciais"):
        return
    op.create_table(
        "leads_comerciais",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("empresa", sa.String(length=200), nullable=True),
        sa.Column("mensagem", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="novo"),
        sa.Column("origem", sa.String(length=80), nullable=False, server_default="landing"),
        sa.Column("notas_internas", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_leads_comerciais_id", "leads_comerciais", ["id"])
    op.create_index("ix_leads_comerciais_email", "leads_comerciais", ["email"])
    op.create_index("ix_leads_comerciais_status", "leads_comerciais", ["status"])
    op.alter_column("leads_comerciais", "status", server_default=None)
    op.alter_column("leads_comerciais", "origem", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("leads_comerciais"):
        return
    op.drop_index("ix_leads_comerciais_status", table_name="leads_comerciais")
    op.drop_index("ix_leads_comerciais_email", table_name="leads_comerciais")
    op.drop_index("ix_leads_comerciais_id", table_name="leads_comerciais")
    op.drop_table("leads_comerciais")
