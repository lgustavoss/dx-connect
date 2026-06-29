"""KB: personalização do portal público (#467).

Revision ID: 057_kb_portal_settings
Revises: 056_kb_motivo_links
Create Date: 2026-06-29
"""

import sqlalchemy as sa
from alembic import op

revision = "057_kb_portal_settings"
down_revision = "056_kb_motivo_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "kb_portal_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("portal_titulo", sa.String(length=120), nullable=True),
        sa.Column("texto_boas_vindas", sa.String(length=500), nullable=True),
        sa.Column("cor_header", sa.String(length=7), server_default="#0B2D4A", nullable=False),
        sa.Column("cor_primaria", sa.String(length=7), server_default="#0D9488", nullable=False),
        sa.Column("cor_texto_header", sa.String(length=7), server_default="#FFFFFF", nullable=False),
        sa.Column("cor_texto_corpo", sa.String(length=7), server_default="#0F172A", nullable=False),
        sa.Column("cor_fundo", sa.String(length=7), server_default="#F8FAFC", nullable=False),
        sa.Column("cor_link", sa.String(length=7), nullable=True),
        sa.Column("exibir_marca_deskrudder", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_kb_portal_settings_tenant_id"),
    )
    op.create_index("ix_kb_portal_settings_tenant_id", "kb_portal_settings", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("kb_portal_settings")
