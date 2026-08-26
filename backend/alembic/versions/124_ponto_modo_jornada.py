"""Ponto: modo_jornada, horario_semana e margem de fecho (#959/#960/#961).

Revision ID: 124_ponto_modo_jornada
Revises: 123_saas_preco_negociado
Create Date: 2026-08-26
"""

import sqlalchemy as sa
from alembic import op

revision = "124_ponto_modo_jornada"
down_revision = "123_saas_preco_negociado"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("atendentes"):
        cols = {c["name"] for c in insp.get_columns("atendentes")}
        if "modo_jornada" not in cols:
            op.add_column(
                "atendentes",
                sa.Column(
                    "modo_jornada",
                    sa.String(20),
                    nullable=False,
                    server_default="nenhum",
                ),
            )
        if "horario_semana_json" not in cols:
            op.add_column(
                "atendentes",
                sa.Column("horario_semana_json", sa.Text(), nullable=True),
            )
        # Backfill: quem já usava ciclo X×Y → modo ciclo
        op.execute(
            sa.text(
                "UPDATE atendentes SET modo_jornada = 'ciclo' "
                "WHERE usa_escala IS TRUE AND modo_jornada = 'nenhum'"
            )
        )

    if insp.has_table("ponto_settings"):
        cols = {c["name"] for c in insp.get_columns("ponto_settings")}
        if "fecho_margem_pos_saida_minutos" not in cols:
            op.add_column(
                "ponto_settings",
                sa.Column(
                    "fecho_margem_pos_saida_minutos",
                    sa.Integer(),
                    nullable=False,
                    server_default="30",
                ),
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("ponto_settings"):
        cols = {c["name"] for c in insp.get_columns("ponto_settings")}
        if "fecho_margem_pos_saida_minutos" in cols:
            op.drop_column("ponto_settings", "fecho_margem_pos_saida_minutos")
    if insp.has_table("atendentes"):
        cols = {c["name"] for c in insp.get_columns("atendentes")}
        if "horario_semana_json" in cols:
            op.drop_column("atendentes", "horario_semana_json")
        if "modo_jornada" in cols:
            op.drop_column("atendentes", "modo_jornada")
