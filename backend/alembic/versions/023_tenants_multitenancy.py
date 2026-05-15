"""tenants, inbound addresses, tenant_id nas entidades principais.

Revision ID: 023_tenants
Revises: 022_email_resend
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "023_tenants"
down_revision = "022_email_resend"
branch_labels = None
depends_on = None


def _drop_unique_if_exists(table: str, name: str) -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    names = {c["name"] for c in insp.get_unique_constraints(table)}
    if name in names:
        op.drop_constraint(name, table, type_="unique")


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute(sa.text("INSERT INTO tenants (id, nome, ativo) VALUES (1, 'Padrão', true)"))
    op.execute(
        sa.text(
            "SELECT setval(pg_get_serial_sequence('tenants', 'id'), "
            "GREATEST(1, COALESCE((SELECT MAX(id) FROM tenants), 1)))"
        )
    )

    for table in ("atendentes", "redes", "empresas", "setores", "tickets"):
        op.add_column(
            table,
            sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="1"),
        )
        op.create_foreign_key(
            f"fk_{table}_tenant_id",
            table,
            "tenants",
            ["tenant_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"], unique=False)

    _drop_unique_if_exists("atendentes", "atendentes_email_key")
    op.create_unique_constraint("uq_atendentes_tenant_email", "atendentes", ["tenant_id", "email"])

    _drop_unique_if_exists("setores", "setores_slug_key")
    op.create_unique_constraint("uq_setores_tenant_slug", "setores", ["tenant_id", "slug"])

    op.create_table(
        "tenant_inbound_addresses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("local_part", sa.String(length=128), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=True),
        sa.Column("setor_id", sa.Integer(), nullable=False),
        sa.Column("default_empresa_id", sa.Integer(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["default_empresa_id"], ["empresas.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["setor_id"], ["setores.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("local_part", name="uq_tenant_inbound_local_part"),
    )
    op.create_index("ix_tenant_inbound_addresses_tenant_id", "tenant_inbound_addresses", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("tenant_inbound_addresses")

    op.drop_constraint("uq_setores_tenant_slug", "setores", type_="unique")
    op.create_unique_constraint("setores_slug_key", "setores", ["slug"])

    op.drop_constraint("uq_atendentes_tenant_email", "atendentes", type_="unique")
    op.create_unique_constraint("atendentes_email_key", "atendentes", ["email"])

    for table in ("tickets", "setores", "empresas", "redes", "atendentes"):
        op.drop_constraint(f"fk_{table}_tenant_id", table, type_="foreignkey")
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_column(table, "tenant_id")

    op.drop_table("tenants")
