"""Implantação: checklist no ticket e ticket automático pós-assinatura (#325).

Revision ID: 103_implantacao_checklist
Revises: 102_ponto_rh_avancado
Create Date: 2026-08-20
"""

import sqlalchemy as sa
from alembic import op

revision = "103_implantacao_checklist"
down_revision = "102_ponto_rh_avancado"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("implantacao_checklist_templates"):
        op.create_table(
            "implantacao_checklist_templates",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("nome", sa.String(120), nullable=False),
            sa.Column("versao", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("setor_id", sa.Integer(), sa.ForeignKey("setores.id", ondelete="SET NULL"), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_implantacao_checklist_templates_setor_id", "implantacao_checklist_templates", ["setor_id"])
        op.create_index("ix_implantacao_checklist_templates_ativo", "implantacao_checklist_templates", ["ativo"])

    if not insp.has_table("implantacao_checklist_template_itens"):
        op.create_table(
            "implantacao_checklist_template_itens",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "template_id",
                sa.Integer(),
                sa.ForeignKey("implantacao_checklist_templates.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("titulo", sa.String(200), nullable=False),
            sa.Column("descricao", sa.Text(), nullable=True),
            sa.Column("ordem", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("obrigatorio", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("chave", sa.String(64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("template_id", "ordem", name="uq_implantacao_template_item_ordem"),
        )
        op.create_index(
            "ix_implantacao_checklist_template_itens_template_id",
            "implantacao_checklist_template_itens",
            ["template_id"],
        )
        op.create_index("ix_implantacao_checklist_template_itens_chave", "implantacao_checklist_template_itens", ["chave"])

    cols = {c["name"] for c in insp.get_columns("tickets")} if insp.has_table("tickets") else set()
    if "contrato_id" not in cols:
        op.add_column(
            "tickets",
            sa.Column(
                "contrato_id",
                sa.Integer(),
                sa.ForeignKey("comercial_contratos.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.create_index("ix_tickets_contrato_id", "tickets", ["contrato_id"], unique=True)

    if not insp.has_table("ticket_checklist_itens"):
        op.create_table(
            "ticket_checklist_itens",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("ticket_id", sa.Integer(), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
            sa.Column(
                "template_item_id",
                sa.Integer(),
                sa.ForeignKey("implantacao_checklist_template_itens.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("titulo", sa.String(200), nullable=False),
            sa.Column("descricao", sa.Text(), nullable=True),
            sa.Column("ordem", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("obrigatorio", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("chave", sa.String(64), nullable=True),
            sa.Column("concluido", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("concluido_por_id", sa.Integer(), sa.ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True),
            sa.Column("concluido_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("observacao", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("ticket_id", "ordem", name="uq_ticket_checklist_item_ordem"),
        )
        op.create_index("ix_ticket_checklist_itens_ticket_id", "ticket_checklist_itens", ["ticket_id"])
        op.create_index("ix_ticket_checklist_itens_chave", "ticket_checklist_itens", ["chave"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("ticket_checklist_itens"):
        op.drop_table("ticket_checklist_itens")
    cols = {c["name"] for c in insp.get_columns("tickets")} if insp.has_table("tickets") else set()
    if "contrato_id" in cols:
        op.drop_index("ix_tickets_contrato_id", table_name="tickets")
        op.drop_column("tickets", "contrato_id")
    if insp.has_table("implantacao_checklist_template_itens"):
        op.drop_table("implantacao_checklist_template_itens")
    if insp.has_table("implantacao_checklist_templates"):
        op.drop_table("implantacao_checklist_templates")
