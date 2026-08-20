"""Ponto v4: horário previsto, feriados, settings (#778–#782).

Revision ID: 102_ponto_rh_avancado
Revises: 101_ponto_justificativas
Create Date: 2026-08-20
"""

import sqlalchemy as sa
from alembic import op

revision = "102_ponto_rh_avancado"
down_revision = "101_ponto_justificativas"
branch_labels = None
depends_on = None


def _colunas(insp, tabela: str) -> set[str]:
    if not insp.has_table(tabela):
        return set()
    return {c["name"] for c in insp.get_columns(tabela)}


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    cols = _colunas(insp, "atendentes")
    if "horario_previsto_entrada" not in cols:
        op.add_column("atendentes", sa.Column("horario_previsto_entrada", sa.String(5), nullable=True))
    if "horario_previsto_saida" not in cols:
        op.add_column("atendentes", sa.Column("horario_previsto_saida", sa.String(5), nullable=True))
    if "tolerancia_atraso_minutos" not in cols:
        op.add_column(
            "atendentes",
            sa.Column("tolerancia_atraso_minutos", sa.Integer(), nullable=False, server_default="0"),
        )

    if not insp.has_table("ponto_settings"):
        op.create_table(
            "ponto_settings",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "tenant_id",
                sa.Integer(),
                sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
                nullable=False,
                unique=True,
            ),
            sa.Column("usar_feriados_nacionais", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("fecho_automatico_ativo", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("fecho_apos_horas", sa.Integer(), nullable=False, server_default="14"),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        )

    if not insp.has_table("ponto_feriados"):
        op.create_table(
            "ponto_feriados",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "tenant_id",
                sa.Integer(),
                sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
                nullable=False,
                index=True,
            ),
            sa.Column("data", sa.Date(), nullable=False),
            sa.Column("nome", sa.String(255), nullable=False),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.UniqueConstraint("tenant_id", "data", name="uq_ponto_feriados_tenant_data"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("ponto_feriados"):
        op.drop_table("ponto_feriados")
    if insp.has_table("ponto_settings"):
        op.drop_table("ponto_settings")
    cols = _colunas(insp, "atendentes")
    for c in ("tolerancia_atraso_minutos", "horario_previsto_saida", "horario_previsto_entrada"):
        if c in cols:
            op.drop_column("atendentes", c)
