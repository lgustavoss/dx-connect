"""Respostas prontas (macros) por setor ou global (#113).

Revision ID: 031_respostas_prontas
Revises: 030_password_reset_tokens
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa

revision = "031_respostas_prontas"
down_revision = "030_password_reset_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "respostas_prontas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("setor_id", sa.Integer(), nullable=True),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("corpo", sa.Text(), nullable=False),
        sa.Column("ordem", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["setor_id"], ["setores.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_respostas_prontas_tenant_id", "respostas_prontas", ["tenant_id"])
    op.create_index("ix_respostas_prontas_setor_id", "respostas_prontas", ["setor_id"])


def downgrade() -> None:
    op.drop_index("ix_respostas_prontas_setor_id", table_name="respostas_prontas")
    op.drop_index("ix_respostas_prontas_tenant_id", table_name="respostas_prontas")
    op.drop_table("respostas_prontas")
