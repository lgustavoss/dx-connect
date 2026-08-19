"""Contrato comercial: templates, documento por CNPJ e versões de PDF (#324 / #349–#352).

Revision ID: 097_comercial_contratos
Revises: 096_comercial_propostas
Create Date: 2026-08-19
"""

import sqlalchemy as sa
from alembic import op

revision = "097_comercial_contratos"
down_revision = "096_comercial_propostas"
branch_labels = None
depends_on = None

_TEMPLATE_PADRAO_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <style>
    body { font-family: DejaVu Sans, Arial, sans-serif; color: #1e293b; margin: 24px; font-size: 13px; }
    h1 { font-size: 20px; margin: 0 0 8px; }
    h2 { font-size: 14px; margin: 20px 0 8px; }
    table { width: 100%; border-collapse: collapse; margin: 8px 0 16px; }
    th, td { border: 1px solid #cbd5e1; padding: 8px; text-align: left; }
    th { background: #f1f5f9; }
    .muted { color: #64748b; font-size: 12px; }
    .logo img { max-height: 72px; }
  </style>
</head>
<body>
  <div class="logo">{{logo}}</div>
  <p class="muted">{{empresa_sistema}}</p>
  <h1>Contrato de prestação de serviços</h1>
  <p><strong>Contratante:</strong> {{razao_social}} &nbsp; <strong>CNPJ:</strong> {{cnpj}}</p>
  <h2>Objeto e valores</h2>
  {{itens}}
  <p><strong>Mensalidade:</strong> {{valor_mensalidade}}</p>
  {{setup_bloco}}
  <h2>Vigência e fidelidade</h2>
  <p>Início: {{data_inicio}} &nbsp; Fim da fidelidade: {{data_fim_fidelidade}} ({{fidelidade_meses}} meses).</p>
  <div>{{fidelidade}}</div>
  <div>{{multa}}</div>
  <div>{{igpm}}</div>
  <h2>Implantação</h2>
  {{clausula_deslocamento}}
  {{clausula_alimentacao}}
  {{clausula_hospedagem}}
</body>
</html>
"""


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("comercial_contrato_templates"):
        op.create_table(
            "comercial_contrato_templates",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("nome", sa.String(120), nullable=False),
            sa.Column("versao", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("conteudo_html", sa.Text(), nullable=False),
            sa.Column("vigencia_inicio", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("nome", "versao", name="uq_comercial_contrato_template_nome_versao"),
        )
        op.create_index("ix_comercial_contrato_templates_nome", "comercial_contrato_templates", ["nome"])
        op.create_index("ix_comercial_contrato_templates_ativo", "comercial_contrato_templates", ["ativo"])

    if not insp.has_table("comercial_contratos"):
        op.create_table(
            "comercial_contratos",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "negociacao_linha_cnpj_id",
                sa.Integer(),
                sa.ForeignKey("crm_negociacao_cnpj_linhas.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column(
                "empresa_id",
                sa.Integer(),
                sa.ForeignKey("empresas.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "template_id",
                sa.Integer(),
                sa.ForeignKey("comercial_contrato_templates.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column(
                "gerado_por_id",
                sa.Integer(),
                sa.ForeignKey("atendentes.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("status", sa.String(20), nullable=False, server_default="rascunho"),
            sa.Column("valor_mensalidade", sa.Numeric(14, 2), nullable=False),
            sa.Column("snapshot_custo", sa.JSON(), nullable=True),
            sa.Column("snapshot_itens", sa.JSON(), nullable=False),
            sa.Column("snapshot_comercial", sa.JSON(), nullable=False),
            sa.Column("data_inicio", sa.Date(), nullable=False),
            sa.Column("data_fim_fidelidade", sa.Date(), nullable=False),
            sa.Column("fidelidade_meses", sa.Integer(), nullable=False, server_default="12"),
            sa.Column("setup_valor", sa.Numeric(14, 2), nullable=True),
            sa.Column("setup_isento", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("deslocamento_cliente", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("alimentacao_cliente", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("hospedagem_cliente", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("multa_max_mensalidades", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("enviado_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("assinado_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_comercial_contratos_linha", "comercial_contratos", ["negociacao_linha_cnpj_id"])
        op.create_index("ix_comercial_contratos_empresa_id", "comercial_contratos", ["empresa_id"])
        op.create_index("ix_comercial_contratos_template_id", "comercial_contratos", ["template_id"])
        op.create_index("ix_comercial_contratos_status", "comercial_contratos", ["status"])
        op.create_index("ix_comercial_contratos_created_at", "comercial_contratos", ["created_at"])

    if not insp.has_table("comercial_contrato_pdfs"):
        op.create_table(
            "comercial_contrato_pdfs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "contrato_id",
                sa.Integer(),
                sa.ForeignKey("comercial_contratos.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "gerado_por_id",
                sa.Integer(),
                sa.ForeignKey("atendentes.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("conteudo_html_snapshot", sa.Text(), nullable=False),
            sa.Column("conteudo_hash", sa.String(64), nullable=False),
            sa.Column("pdf_storage_key", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_comercial_contrato_pdfs_contrato_id", "comercial_contrato_pdfs", ["contrato_id"])
        op.create_index("ix_comercial_contrato_pdfs_created_at", "comercial_contrato_pdfs", ["created_at"])

    bind.execute(
        sa.text(
            """
            INSERT INTO comercial_contrato_templates (nome, versao, conteudo_html, vigencia_inicio, ativo)
            SELECT :nome, 1, :html, CURRENT_TIMESTAMP, true
            WHERE NOT EXISTS (SELECT 1 FROM comercial_contrato_templates LIMIT 1)
            """
        ),
        {"nome": "Padrão", "html": _TEMPLATE_PADRAO_HTML},
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("comercial_contrato_pdfs"):
        op.drop_table("comercial_contrato_pdfs")
    if insp.has_table("comercial_contratos"):
        op.drop_table("comercial_contratos")
    if insp.has_table("comercial_contrato_templates"):
        op.drop_table("comercial_contrato_templates")
