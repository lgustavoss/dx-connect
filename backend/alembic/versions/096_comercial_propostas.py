"""Proposta comercial: templates versionados e documentos gerados (#323 / #345–#347).

Revision ID: 096_comercial_propostas
Revises: 095_web_push
Create Date: 2026-08-18
"""

import sqlalchemy as sa
from alembic import op

revision = "096_comercial_propostas"
down_revision = "095_web_push"
branch_labels = None
depends_on = None

# Sem as palavras «custo»/«margem» — o HTML do cliente não deve carregá-las.
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
  <h1>Proposta comercial</h1>
  <p><strong>Cliente:</strong> {{razao_social}} &nbsp; <strong>CNPJ:</strong> {{cnpj}}</p>
  <h2>Itens</h2>
  {{itens}}
  <p><strong>Valor mensal:</strong> {{valor_mensalidade}}</p>
  <h2>Condições</h2>
  <div>{{condicoes}}</div>
</body>
</html>
"""


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("comercial_proposta_templates"):
        op.create_table(
            "comercial_proposta_templates",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("nome", sa.String(120), nullable=False),
            sa.Column("versao", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("conteudo_html", sa.Text(), nullable=False),
            sa.Column("vigencia_inicio", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("nome", "versao", name="uq_comercial_proposta_template_nome_versao"),
        )
        op.create_index("ix_comercial_proposta_templates_nome", "comercial_proposta_templates", ["nome"])
        op.create_index("ix_comercial_proposta_templates_ativo", "comercial_proposta_templates", ["ativo"])

    if not insp.has_table("comercial_propostas"):
        op.create_table(
            "comercial_propostas",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "negociacao_id",
                sa.Integer(),
                sa.ForeignKey("crm_negociacoes.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "template_id",
                sa.Integer(),
                sa.ForeignKey("comercial_proposta_templates.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column(
                "gerado_por_id",
                sa.Integer(),
                sa.ForeignKey("atendentes.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("status", sa.String(20), nullable=False, server_default="rascunho"),
            sa.Column("conteudo_html_snapshot", sa.Text(), nullable=False),
            sa.Column("conteudo_hash", sa.String(64), nullable=False),
            sa.Column("linha_ids", sa.JSON(), nullable=False),
            sa.Column("pdf_storage_key", sa.String(255), nullable=True),
            sa.Column("canal", sa.String(20), nullable=True),
            sa.Column("enviado_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_comercial_propostas_negociacao_id", "comercial_propostas", ["negociacao_id"])
        op.create_index("ix_comercial_propostas_template_id", "comercial_propostas", ["template_id"])
        op.create_index("ix_comercial_propostas_status", "comercial_propostas", ["status"])
        op.create_index("ix_comercial_propostas_created_at", "comercial_propostas", ["created_at"])

    bind.execute(
        sa.text(
            """
            INSERT INTO comercial_proposta_templates (nome, versao, conteudo_html, vigencia_inicio, ativo)
            SELECT :nome, 1, :html, CURRENT_TIMESTAMP, true
            WHERE NOT EXISTS (SELECT 1 FROM comercial_proposta_templates LIMIT 1)
            """
        ),
        {"nome": "Padrão", "html": _TEMPLATE_PADRAO_HTML},
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("comercial_propostas"):
        op.drop_table("comercial_propostas")
    if insp.has_table("comercial_proposta_templates"):
        op.drop_table("comercial_proposta_templates")
