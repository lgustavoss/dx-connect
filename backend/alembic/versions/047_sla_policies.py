"""SLA: business_calendars, sla_policies e campos em tickets (#277).

Revision ID: 047_sla_policies
Revises: 046_routing_rules
Create Date: 2026-06-23
"""

import sqlalchemy as sa
from alembic import op

revision = "047_sla_policies"
down_revision = "046_routing_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "business_calendars",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("setor_id", sa.Integer(), nullable=True),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("horario_timezone", sa.String(length=64), nullable=False, server_default="America/Sao_Paulo"),
        sa.Column("horario_inicio", sa.String(length=5), nullable=True),
        sa.Column("horario_fim", sa.String(length=5), nullable=True),
        sa.Column("horario_semana_json", sa.Text(), nullable=True),
        sa.Column("usar_feriados_nacionais", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["setor_id"], ["setores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_business_calendars_id"), "business_calendars", ["id"], unique=False)
    op.create_index(op.f("ix_business_calendars_tenant_id"), "business_calendars", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_business_calendars_setor_id"), "business_calendars", ["setor_id"], unique=False)

    op.create_table(
        "sla_policies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("setor_id", sa.Integer(), nullable=False),
        sa.Column("prioridade", sa.String(length=20), nullable=True),
        sa.Column("business_calendar_id", sa.Integer(), nullable=True),
        sa.Column("meta_primeira_resposta_min", sa.Integer(), nullable=True),
        sa.Column("meta_resolucao_min", sa.Integer(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["business_calendar_id"], ["business_calendars.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["setor_id"], ["setores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "setor_id", "prioridade", name="uq_sla_policies_setor_prioridade"),
    )
    op.create_index(op.f("ix_sla_policies_id"), "sla_policies", ["id"], unique=False)
    op.create_index(op.f("ix_sla_policies_tenant_id"), "sla_policies", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_sla_policies_setor_id"), "sla_policies", ["setor_id"], unique=False)
    op.create_index(op.f("ix_sla_policies_prioridade"), "sla_policies", ["prioridade"], unique=False)

    op.add_column("tickets", sa.Column("sla_policy_id", sa.Integer(), nullable=True))
    op.add_column("tickets", sa.Column("sla_meta_primeira_resposta_min", sa.Integer(), nullable=True))
    op.add_column("tickets", sa.Column("sla_meta_resolucao_min", sa.Integer(), nullable=True))
    op.add_column("tickets", sa.Column("sla_primeira_resposta_vence_em", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tickets", sa.Column("sla_resolucao_vence_em", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tickets", sa.Column("sla_primeira_resposta_em", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "tickets",
        sa.Column("sla_violado", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_foreign_key(
        "fk_tickets_sla_policy_id",
        "tickets",
        "sla_policies",
        ["sla_policy_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_tickets_sla_policy_id"), "tickets", ["sla_policy_id"], unique=False)
    op.alter_column("tickets", "sla_violado", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_tickets_sla_policy_id"), table_name="tickets")
    op.drop_constraint("fk_tickets_sla_policy_id", "tickets", type_="foreignkey")
    op.drop_column("tickets", "sla_violado")
    op.drop_column("tickets", "sla_primeira_resposta_em")
    op.drop_column("tickets", "sla_resolucao_vence_em")
    op.drop_column("tickets", "sla_primeira_resposta_vence_em")
    op.drop_column("tickets", "sla_meta_resolucao_min")
    op.drop_column("tickets", "sla_meta_primeira_resposta_min")
    op.drop_column("tickets", "sla_policy_id")

    op.drop_index(op.f("ix_sla_policies_prioridade"), table_name="sla_policies")
    op.drop_index(op.f("ix_sla_policies_setor_id"), table_name="sla_policies")
    op.drop_index(op.f("ix_sla_policies_tenant_id"), table_name="sla_policies")
    op.drop_index(op.f("ix_sla_policies_id"), table_name="sla_policies")
    op.drop_table("sla_policies")

    op.drop_index(op.f("ix_business_calendars_setor_id"), table_name="business_calendars")
    op.drop_index(op.f("ix_business_calendars_tenant_id"), table_name="business_calendars")
    op.drop_index(op.f("ix_business_calendars_id"), table_name="business_calendars")
    op.drop_table("business_calendars")
