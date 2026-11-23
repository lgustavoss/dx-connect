"""Assinatura eletrônica multiparte — envelope + partes (#1380 / #1429).

Aditiva: ``contrato_assinaturas`` + ``contrato_assinatura_partes`` + índice
único parcial (um envelope ativo por contrato).

Revision ID: 164_contrato_assinaturas
Revises: 163_funcionario_rede_vinculo
Create Date: 2026-11-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "164_contrato_assinaturas"
down_revision = "163_funcionario_rede_vinculo"
branch_labels = None
depends_on = None

TABELA = "contrato_assinaturas"
TABELA_PARTES = "contrato_assinatura_partes"
INDICE_ATIVO = "uq_contrato_assinatura_ativa"


def _tabelas() -> set[str]:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return set(insp.get_table_names())


def _indices(tabela: str) -> set[str]:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if tabela not in insp.get_table_names():
        return set()
    return {i["name"] for i in insp.get_indexes(tabela)}


def upgrade() -> None:
    if TABELA not in _tabelas():
        op.create_table(
            TABELA,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "contrato_id",
                sa.Integer(),
                sa.ForeignKey("comercial_contratos.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("provedor", sa.String(length=20), nullable=False, server_default="docuseal"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="pendente"),
            sa.Column("submission_id", sa.String(length=80), nullable=True),
            sa.Column("submitter_slug", sa.String(length=120), nullable=True),
            sa.Column("link_assinatura", sa.String(length=500), nullable=True),
            sa.Column("enviado_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("visualizado_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("assinado_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expira_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("pdf_assinado_path", sa.String(length=255), nullable=True),
            sa.Column("audit_log_path", sa.String(length=255), nullable=True),
            sa.Column("selfie_path", sa.String(length=255), nullable=True),
            sa.Column("pdf_sha256", sa.String(length=64), nullable=True),
            sa.Column("audit_sha256", sa.String(length=64), nullable=True),
            sa.Column(
                "criado_por_id",
                sa.Integer(),
                sa.ForeignKey("atendentes.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("ultimo_erro", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_contrato_assinaturas_contrato_id", TABELA, ["contrato_id"])
        op.create_index("ix_contrato_assinaturas_provedor", TABELA, ["provedor"])
        op.create_index("ix_contrato_assinaturas_status", TABELA, ["status"])
        op.create_index("ix_contrato_assinaturas_submission_id", TABELA, ["submission_id"])

    if INDICE_ATIVO not in _indices(TABELA):
        op.create_index(
            INDICE_ATIVO,
            TABELA,
            ["contrato_id"],
            unique=True,
            postgresql_where=sa.text(
                "status IN ('pendente', 'enviado', 'visualizado', 'parcial')"
            ),
            sqlite_where=sa.text(
                "status IN ('pendente', 'enviado', 'visualizado', 'parcial')"
            ),
        )

    if TABELA_PARTES not in _tabelas():
        op.create_table(
            TABELA_PARTES,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "assinatura_id",
                sa.Integer(),
                sa.ForeignKey("contrato_assinaturas.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("papel", sa.String(length=20), nullable=False),
            sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("nome", sa.String(length=200), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("cpf", sa.String(length=11), nullable=True),
            sa.Column("telefone", sa.String(length=40), nullable=True),
            sa.Column("role_docuseal", sa.String(length=80), nullable=False),
            sa.Column("submitter_slug", sa.String(length=120), nullable=True),
            sa.Column("link_assinatura", sa.String(length=500), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="enviado"),
            sa.Column("visualizado_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("assinado_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ultimo_erro", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_contrato_assinatura_partes_assinatura_id", TABELA_PARTES, ["assinatura_id"])
        op.create_index("ix_contrato_assinatura_partes_papel", TABELA_PARTES, ["papel"])
        op.create_index("ix_contrato_assinatura_partes_slug", TABELA_PARTES, ["submitter_slug"])


def downgrade() -> None:
    if TABELA_PARTES in _tabelas():
        op.drop_table(TABELA_PARTES)
    if INDICE_ATIVO in _indices(TABELA):
        op.drop_index(INDICE_ATIVO, table_name=TABELA)
    if TABELA in _tabelas():
        op.drop_table(TABELA)
