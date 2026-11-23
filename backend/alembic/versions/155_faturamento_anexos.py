"""Anexos manuais de boleto/NFS-e na fatura aprovada (#326 / #364 / #368).

Revision ID: 155_faturamento_anexos
Revises: 154_deskremote_enroll
Create Date: 2026-10-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "155_faturamento_anexos"
down_revision = "154_deskremote_enroll"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("faturamento_faturas"):
        cols = {c["name"] for c in insp.get_columns("faturamento_faturas")}
        if "boleto_linha_digitavel" not in cols:
            op.add_column(
                "faturamento_faturas",
                sa.Column("boleto_linha_digitavel", sa.String(60), nullable=True),
            )
        if "boleto_nosso_numero" not in cols:
            op.add_column(
                "faturamento_faturas",
                sa.Column("boleto_nosso_numero", sa.String(40), nullable=True),
            )
        if "nfse_numero" not in cols:
            op.add_column(
                "faturamento_faturas",
                sa.Column("nfse_numero", sa.String(40), nullable=True),
            )

    if not insp.has_table("faturamento_anexos"):
        op.create_table(
            "faturamento_anexos",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "fatura_id",
                sa.Integer(),
                sa.ForeignKey("faturamento_faturas.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("tipo", sa.String(20), nullable=False),
            sa.Column("nome_original", sa.String(255), nullable=False),
            sa.Column("content_type", sa.String(128), nullable=True),
            sa.Column("tamanho_bytes", sa.Integer(), nullable=False),
            sa.Column("storage_key", sa.String(500), nullable=False),
            sa.Column(
                "enviado_por_id",
                sa.Integer(),
                sa.ForeignKey("atendentes.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("fatura_id", "tipo", name="uq_faturamento_anexo_fatura_tipo"),
        )
        op.create_index("ix_faturamento_anexos_fatura_id", "faturamento_anexos", ["fatura_id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("faturamento_anexos"):
        op.drop_table("faturamento_anexos")
    if insp.has_table("faturamento_faturas"):
        cols = {c["name"] for c in insp.get_columns("faturamento_faturas")}
        for col in ("nfse_numero", "boleto_nosso_numero", "boleto_linha_digitavel"):
            if col in cols:
                op.drop_column("faturamento_faturas", col)
