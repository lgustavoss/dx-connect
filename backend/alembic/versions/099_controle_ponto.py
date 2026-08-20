"""Controle de ponto: batidas + escala no atendente (#761+).

Revision ID: 099_controle_ponto
Revises: 098_comercial_contratos_f2
Create Date: 2026-08-20
"""

import sqlalchemy as sa
from alembic import op

revision = "099_controle_ponto"
down_revision = "098_comercial_contratos_f2"
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
    if "usa_escala" not in cols:
        op.add_column(
            "atendentes",
            sa.Column("usa_escala", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )
    if "escala_horas_trabalho" not in cols:
        op.add_column("atendentes", sa.Column("escala_horas_trabalho", sa.Integer(), nullable=True))
    if "escala_horas_folga" not in cols:
        op.add_column("atendentes", sa.Column("escala_horas_folga", sa.Integer(), nullable=True))
    if "escala_inicio_em" not in cols:
        op.add_column("atendentes", sa.Column("escala_inicio_em", sa.Date(), nullable=True))

    if not insp.has_table("ponto_batidas"):
        op.create_table(
            "ponto_batidas",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "tenant_id",
                sa.Integer(),
                sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "atendente_id",
                sa.Integer(),
                sa.ForeignKey("atendentes.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("tipo", sa.String(20), nullable=False),
            sa.Column("registrado_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("origem", sa.String(20), nullable=True),
            sa.Column("ip", sa.String(64), nullable=True),
            sa.Column("user_agent", sa.String(512), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        )
        op.create_index("ix_ponto_batidas_atendente_registrado", "ponto_batidas", ["atendente_id", "registrado_em"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("ponto_batidas"):
        op.drop_index("ix_ponto_batidas_atendente_registrado", table_name="ponto_batidas")
        op.drop_table("ponto_batidas")
    cols = _colunas(insp, "atendentes")
    for col in ("escala_inicio_em", "escala_horas_folga", "escala_horas_trabalho", "usa_escala"):
        if col in cols:
            op.drop_column("atendentes", col)
