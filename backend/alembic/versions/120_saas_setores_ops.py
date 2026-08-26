"""Setores da equipe SaaS no control-plane.

Revision ID: 120_saas_setores_ops
Revises: 119_chat_canal_setor_backfill
Create Date: 2026-08-25
"""

import sqlalchemy as sa
from alembic import op

revision = "120_saas_setores_ops"
down_revision = "119_chat_canal_setor_backfill"
branch_labels = None
depends_on = None

_SEED = ("Admin", "Desenvolvimento", "Comercial")


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("saas_setores"):
        op.create_table(
            "saas_setores",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("nome", sa.String(length=100), nullable=False),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_saas_setores_tenant_id", "saas_setores", ["tenant_id"])
        op.create_unique_constraint("uq_saas_setores_tenant_nome", "saas_setores", ["tenant_id", "nome"])
    else:
        idxs = {i["name"] for i in insp.get_indexes("saas_setores")}
        if "ix_saas_setores_tenant_id" not in idxs:
            op.create_index("ix_saas_setores_tenant_id", "saas_setores", ["tenant_id"])
        uqs = {c["name"] for c in insp.get_unique_constraints("saas_setores")}
        if "uq_saas_setores_tenant_nome" not in uqs:
            op.create_unique_constraint("uq_saas_setores_tenant_nome", "saas_setores", ["tenant_id", "nome"])

    if not insp.has_table("saas_ops_setor"):
        op.create_table(
            "saas_ops_setor",
            sa.Column(
                "atendente_id",
                sa.Integer(),
                sa.ForeignKey("atendentes.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column(
                "saas_setor_id",
                sa.Integer(),
                sa.ForeignKey("saas_setores.id", ondelete="CASCADE"),
                primary_key=True,
            ),
        )

    tenants = bind.execute(sa.text("SELECT id FROM tenants")).fetchall()
    for (tid,) in tenants:
        for nome in _SEED:
            bind.execute(
                sa.text(
                    "INSERT INTO saas_setores (tenant_id, nome, ativo) "
                    "VALUES (:tid, :nome, true) "
                    "ON CONFLICT ON CONSTRAINT uq_saas_setores_tenant_nome DO NOTHING"
                ),
                {"tid": tid, "nome": nome},
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("saas_ops_setor"):
        op.drop_table("saas_ops_setor")
    if insp.has_table("saas_setores"):
        idxs = {i["name"] for i in insp.get_indexes("saas_setores")}
        if "ix_saas_setores_tenant_id" in idxs:
            op.drop_index("ix_saas_setores_tenant_id", table_name="saas_setores")
        op.drop_table("saas_setores")
