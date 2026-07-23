"""Provisionamento, trial e renovações SaaS (#524 / #527 / #528).

Revision ID: 079_saas_provision_trial_renovacao
Revises: 078_cliente_saas
Create Date: 2026-07-23
"""

import sqlalchemy as sa
from alembic import op

revision = "079_saas_provision_trial_renovacao"
down_revision = "078_cliente_saas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("clientes_saas"):
        cols = {c["name"] for c in insp.get_columns("clientes_saas")}
        if "contato_email" not in cols:
            op.add_column("clientes_saas", sa.Column("contato_email", sa.String(length=255), nullable=True))
        if "contato_nome" not in cols:
            op.add_column("clientes_saas", sa.Column("contato_nome", sa.String(length=200), nullable=True))
        if "api_port" not in cols:
            op.add_column("clientes_saas", sa.Column("api_port", sa.Integer(), nullable=True))
        if "provisionamento_status" not in cols:
            op.add_column("clientes_saas", sa.Column("provisionamento_status", sa.String(length=32), nullable=True))
        if "provisionamento_mensagem" not in cols:
            op.add_column("clientes_saas", sa.Column("provisionamento_mensagem", sa.Text(), nullable=True))
        if "provisionamento_atualizado_em" not in cols:
            op.add_column(
                "clientes_saas",
                sa.Column("provisionamento_atualizado_em", sa.DateTime(timezone=True), nullable=True),
            )

    if not insp.has_table("saas_alerta_emitidos"):
        op.create_table(
            "saas_alerta_emitidos",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("cliente_saas_id", sa.Integer(), sa.ForeignKey("clientes_saas.id", ondelete="CASCADE"), nullable=False),
            sa.Column("evento", sa.String(length=40), nullable=False),
            sa.Column("referencia_data", sa.Date(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint(
                "cliente_saas_id",
                "evento",
                "referencia_data",
                name="uq_saas_alerta_emitidos_cliente_evento_ref",
            ),
        )
        op.create_index("ix_saas_alerta_emitidos_id", "saas_alerta_emitidos", ["id"])
        op.create_index("ix_saas_alerta_emitidos_cliente_saas_id", "saas_alerta_emitidos", ["cliente_saas_id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("saas_alerta_emitidos"):
        op.drop_index("ix_saas_alerta_emitidos_cliente_saas_id", table_name="saas_alerta_emitidos")
        op.drop_index("ix_saas_alerta_emitidos_id", table_name="saas_alerta_emitidos")
        op.drop_table("saas_alerta_emitidos")
    if insp.has_table("clientes_saas"):
        cols = {c["name"] for c in insp.get_columns("clientes_saas")}
        for col in (
            "provisionamento_atualizado_em",
            "provisionamento_mensagem",
            "provisionamento_status",
            "api_port",
            "contato_nome",
            "contato_email",
        ):
            if col in cols:
                op.drop_column("clientes_saas", col)
