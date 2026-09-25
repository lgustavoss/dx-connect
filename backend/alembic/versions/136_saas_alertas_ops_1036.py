"""Alertas operacionais por instância — migration #1036 / #1037.

Revision ID: 136_saas_alertas_ops_1036
Revises: 135_wpp_midia_retencao_899
Create Date: 2026-09-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "136_saas_alertas_ops_1036"
down_revision = "135_wpp_midia_retencao_899"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "saas_alertas_ops",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cliente_saas_id", sa.Integer(), sa.ForeignKey("clientes_saas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("codigo_sinal", sa.String(length=64), nullable=False),
        sa.Column("modulo", sa.String(length=32), nullable=False),
        sa.Column("severidade", sa.String(length=16), nullable=False),
        sa.Column("estado", sa.String(length=16), nullable=False, server_default="ativo"),
        sa.Column("ciclo_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("mitigated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("evidencia", sa.JSON(), nullable=True),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "cliente_saas_id",
            "codigo_sinal",
            "ciclo_id",
            name="uq_saas_alertas_ops_cliente_sinal_ciclo",
        ),
    )
    op.create_index("ix_saas_alertas_ops_cliente_saas_id", "saas_alertas_ops", ["cliente_saas_id"])
    op.create_index("ix_saas_alertas_ops_codigo_sinal", "saas_alertas_ops", ["codigo_sinal"])
    op.create_index("ix_saas_alertas_ops_modulo", "saas_alertas_ops", ["modulo"])
    op.create_index("ix_saas_alertas_ops_severidade", "saas_alertas_ops", ["severidade"])
    op.create_index("ix_saas_alertas_ops_estado", "saas_alertas_ops", ["estado"])

    op.create_table(
        "saas_alertas_ops_eventos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("alerta_id", sa.Integer(), sa.ForeignKey("saas_alertas_ops.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.Column("mensagem", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_saas_alertas_ops_eventos_alerta_id", "saas_alertas_ops_eventos", ["alerta_id"])


def downgrade() -> None:
    op.drop_index("ix_saas_alertas_ops_eventos_alerta_id", table_name="saas_alertas_ops_eventos")
    op.drop_table("saas_alertas_ops_eventos")
    op.drop_index("ix_saas_alertas_ops_estado", table_name="saas_alertas_ops")
    op.drop_index("ix_saas_alertas_ops_severidade", table_name="saas_alertas_ops")
    op.drop_index("ix_saas_alertas_ops_modulo", table_name="saas_alertas_ops")
    op.drop_index("ix_saas_alertas_ops_codigo_sinal", table_name="saas_alertas_ops")
    op.drop_index("ix_saas_alertas_ops_cliente_saas_id", table_name="saas_alertas_ops")
    op.drop_table("saas_alertas_ops")
