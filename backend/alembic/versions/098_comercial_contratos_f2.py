"""Contratos F2: dados fiscais, reajuste configurável, PDF assinado e conversão (#353 #354 #357).

Revision ID: 098_comercial_contratos_f2
Revises: 097_comercial_contratos
Create Date: 2026-08-19
"""

import sqlalchemy as sa
from alembic import op

revision = "098_comercial_contratos_f2"
down_revision = "097_comercial_contratos"
branch_labels = None
depends_on = None


def _colunas(insp, tabela: str) -> set[str]:
    if not insp.has_table(tabela):
        return set()
    return {c["name"] for c in insp.get_columns(tabela)}


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    neg_cols = _colunas(insp, "crm_negociacoes")
    if "nome_base_webposto" not in neg_cols:
        op.add_column("crm_negociacoes", sa.Column("nome_base_webposto", sa.String(255), nullable=True))

    linha_cols = _colunas(insp, "crm_negociacao_cnpj_linhas")
    if "dados_fiscais" not in linha_cols:
        op.add_column("crm_negociacao_cnpj_linhas", sa.Column("dados_fiscais", sa.JSON(), nullable=True))

    ctr_cols = _colunas(insp, "comercial_contratos")
    if "reajuste_percentual" not in ctr_cols:
        op.add_column(
            "comercial_contratos",
            sa.Column("reajuste_percentual", sa.Numeric(7, 4), nullable=False, server_default="0"),
        )
    if "reajuste_rotulo" not in ctr_cols:
        op.add_column(
            "comercial_contratos",
            sa.Column("reajuste_rotulo", sa.String(80), nullable=False, server_default=""),
        )
    op.alter_column("comercial_contratos", "reajuste_percentual", server_default=None)
    op.alter_column("comercial_contratos", "reajuste_rotulo", server_default=None)
    if "pdf_assinado_storage_key" not in ctr_cols:
        op.add_column("comercial_contratos", sa.Column("pdf_assinado_storage_key", sa.String(255), nullable=True))
    if "pdf_assinado_nome_original" not in ctr_cols:
        op.add_column("comercial_contratos", sa.Column("pdf_assinado_nome_original", sa.String(255), nullable=True))
    if "referencia_externa" not in ctr_cols:
        op.add_column("comercial_contratos", sa.Column("referencia_externa", sa.String(120), nullable=True))

    if not insp.has_table("comercial_contrato_politica"):
        op.create_table(
            "comercial_contrato_politica",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("reajuste_percentual", sa.Numeric(7, 4), nullable=False, server_default="0"),
            sa.Column("reajuste_rotulo", sa.String(80), nullable=False, server_default=""),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        bind.execute(
            sa.text(
                "INSERT INTO comercial_contrato_politica (id, reajuste_percentual, reajuste_rotulo) "
                "SELECT 1, 0, '' WHERE NOT EXISTS (SELECT 1 FROM comercial_contrato_politica LIMIT 1)"
            )
        )
    op.alter_column("comercial_contrato_politica", "reajuste_percentual", server_default=None)
    op.alter_column("comercial_contrato_politica", "reajuste_rotulo", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("comercial_contrato_politica"):
        op.drop_table("comercial_contrato_politica")
    ctr_cols = _colunas(insp, "comercial_contratos")
    for col in (
        "referencia_externa",
        "pdf_assinado_nome_original",
        "pdf_assinado_storage_key",
        "reajuste_rotulo",
        "reajuste_percentual",
    ):
        if col in ctr_cols:
            op.drop_column("comercial_contratos", col)
    if "dados_fiscais" in _colunas(insp, "crm_negociacao_cnpj_linhas"):
        op.drop_column("crm_negociacao_cnpj_linhas", "dados_fiscais")
    if "nome_base_webposto" in _colunas(insp, "crm_negociacoes"):
        op.drop_column("crm_negociacoes", "nome_base_webposto")
