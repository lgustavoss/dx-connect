"""Configuração de distribuição automática de tickets por setor.

Revision ID: 043_setor_distribuicao
Revises: 042_atendente_notificacao
Create Date: 2026-06-14
"""

from alembic import op
import sqlalchemy as sa

revision = "043_setor_distribuicao"
down_revision = "042_atendente_notificacao"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "setores",
        sa.Column("distribuicao_modo", sa.String(length=30), nullable=False, server_default="manual"),
    )
    op.add_column(
        "setores",
        sa.Column("distribuicao_timeout_minutos", sa.Integer(), nullable=False, server_default="30"),
    )
    op.add_column(
        "setores",
        sa.Column("distribuicao_estrategia", sa.String(length=30), nullable=False, server_default="round_robin"),
    )
    op.add_column(
        "setores",
        sa.Column("distribuicao_atendentes_elegiveis", sa.JSON(), nullable=True),
    )
    op.add_column(
        "tickets",
        sa.Column("fila_desde_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "setor_distribuicao_round_robin",
        sa.Column("setor_id", sa.Integer(), nullable=False),
        sa.Column("last_atendente_id", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["last_atendente_id"], ["atendentes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["setor_id"], ["setores.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("setor_id"),
    )
    op.execute(
        """
        UPDATE tickets
        SET fila_desde_at = created_at
        WHERE atendente_id IS NULL AND fechado_em IS NULL AND fila_desde_at IS NULL
        """
    )


def downgrade() -> None:
    op.drop_table("setor_distribuicao_round_robin")
    op.drop_column("tickets", "fila_desde_at")
    op.drop_column("setores", "distribuicao_atendentes_elegiveis")
    op.drop_column("setores", "distribuicao_estrategia")
    op.drop_column("setores", "distribuicao_timeout_minutos")
    op.drop_column("setores", "distribuicao_modo")
