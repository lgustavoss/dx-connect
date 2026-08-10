"""CRM — funil, leads e negociações (#322 / #083 → #084).

Revision ID: 084_crm_leads_negociacao
Revises: 083_comercial_custos_tier_posto
Create Date: 2026-08-10
"""

import sqlalchemy as sa
from alembic import op

revision = "084_crm_leads_negociacao"
down_revision = "083_comercial_custos_tier_posto"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("crm_funil_estagios"):
        op.create_table(
            "crm_funil_estagios",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("slug", sa.String(50), nullable=False),
            sa.Column("nome", sa.String(120), nullable=False),
            sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("tipo", sa.String(20), nullable=False, server_default="aberto"),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("slug", name="uq_crm_funil_estagio_slug"),
        )
        op.create_index("ix_crm_funil_estagios_slug", "crm_funil_estagios", ["slug"])
        op.create_index("ix_crm_funil_estagios_ordem", "crm_funil_estagios", ["ordem"])

    if not insp.has_table("crm_leads"):
        op.create_table(
            "crm_leads",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("nome", sa.String(255), nullable=False),
            sa.Column("telefone", sa.String(40), nullable=True),
            sa.Column("email", sa.String(255), nullable=True),
            sa.Column("empresa_texto", sa.String(255), nullable=True),
            sa.Column("origem", sa.String(80), nullable=True),
            sa.Column("notas", sa.Text(), nullable=True),
            sa.Column("responsavel_id", sa.Integer(), sa.ForeignKey("atendentes.id", ondelete="RESTRICT"), nullable=False),
            sa.Column(
                "estagio_id",
                sa.Integer(),
                sa.ForeignKey("crm_funil_estagios.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("perdido_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_crm_leads_responsavel_id", "crm_leads", ["responsavel_id"])
        op.create_index("ix_crm_leads_estagio_id", "crm_leads", ["estagio_id"])

    if not insp.has_table("crm_negociacoes"):
        op.create_table(
            "crm_negociacoes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("lead_id", sa.Integer(), sa.ForeignKey("crm_leads.id", ondelete="CASCADE"), nullable=False),
            sa.Column("responsavel_id", sa.Integer(), sa.ForeignKey("atendentes.id", ondelete="RESTRICT"), nullable=False),
            sa.Column(
                "estagio_id",
                sa.Integer(),
                sa.ForeignKey("crm_funil_estagios.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("ativa", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("titulo", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_crm_negociacoes_lead_id", "crm_negociacoes", ["lead_id"])
        op.create_index("ix_crm_negociacoes_responsavel_id", "crm_negociacoes", ["responsavel_id"])
        op.create_index("ix_crm_negociacoes_estagio_id", "crm_negociacoes", ["estagio_id"])
        op.create_index("ix_crm_negociacoes_ativa", "crm_negociacoes", ["ativa"])

    if not insp.has_table("crm_negociacao_cnpj_linhas"):
        op.create_table(
            "crm_negociacao_cnpj_linhas",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "negociacao_id",
                sa.Integer(),
                sa.ForeignKey("crm_negociacoes.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("cnpj", sa.String(18), nullable=True),
            sa.Column("razao_social", sa.String(255), nullable=True),
            sa.Column("item_ids", sa.JSON(), nullable=False),
            sa.Column("quantidade_pdvs", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("desconto_posto_100k", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("tef_override", sa.JSON(), nullable=True),
            sa.Column("valor_negociado", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("snapshot_custo", sa.JSON(), nullable=True),
            sa.Column("total_custo", sa.Numeric(14, 2), nullable=True),
            sa.Column("margem_calculada", sa.Numeric(14, 2), nullable=True),
            sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id", ondelete="SET NULL"), nullable=True),
            sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_crm_negociacao_cnpj_linhas_negociacao_id", "crm_negociacao_cnpj_linhas", ["negociacao_id"])
        op.create_index("ix_crm_negociacao_cnpj_linhas_cnpj", "crm_negociacao_cnpj_linhas", ["cnpj"])

    if not insp.has_table("crm_negociacao_atividades"):
        op.create_table(
            "crm_negociacao_atividades",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "negociacao_id",
                sa.Integer(),
                sa.ForeignKey("crm_negociacoes.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("autor_id", sa.Integer(), sa.ForeignKey("atendentes.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("tipo", sa.String(40), nullable=False, server_default="nota"),
            sa.Column("texto", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index(
            "ix_crm_negociacao_atividades_negociacao_id", "crm_negociacao_atividades", ["negociacao_id"]
        )
        op.create_index("ix_crm_negociacao_atividades_created_at", "crm_negociacao_atividades", ["created_at"])

    # Seed funil padrão se vazio
    conn = op.get_bind()
    count = conn.execute(sa.text("SELECT COUNT(*) FROM crm_funil_estagios")).scalar()
    if not count:
        rows = [
            ("lead", "Lead", 10, "aberto"),
            ("em_negociacao", "Em negociação", 20, "aberto"),
            ("documentacao", "Documentação", 30, "aberto"),
            ("proposta_enviada", "Proposta enviada", 40, "aberto"),
            ("contrato_assinado", "Contrato assinado", 50, "ganho"),
            ("implantacao", "Implantação", 60, "ganho"),
            ("perdido", "Perdido", 90, "perdido"),
        ]
        for slug, nome, ordem, tipo in rows:
            conn.execute(
                sa.text(
                    "INSERT INTO crm_funil_estagios (slug, nome, ordem, tipo, ativo) "
                    "VALUES (:slug, :nome, :ordem, :tipo, true)"
                ),
                {"slug": slug, "nome": nome, "ordem": ordem, "tipo": tipo},
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    for table in (
        "crm_negociacao_atividades",
        "crm_negociacao_cnpj_linhas",
        "crm_negociacoes",
        "crm_leads",
        "crm_funil_estagios",
    ):
        if insp.has_table(table):
            op.drop_table(table)
