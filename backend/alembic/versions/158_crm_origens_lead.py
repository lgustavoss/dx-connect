"""Origens do lead configuráveis (#1319).

Revision ID: 158_crm_origens_lead
Revises: 157_merge_fcm_faturamento
Create Date: 2026-11-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "158_crm_origens_lead"
down_revision = "157_merge_fcm_faturamento"
branch_labels = None
depends_on = None

SEED = (("WhatsApp", 10), ("Indicação", 20), ("Site", 30), ("Visita", 40), ("Outro", 50))


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("crm_origens_lead"):
        op.create_table(
            "crm_origens_lead",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("nome", sa.String(80), nullable=False),
            sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("nome", name="uq_crm_origem_lead_nome"),
        )
        op.create_index("ix_crm_origens_lead_nome", "crm_origens_lead", ["nome"])
        op.create_index("ix_crm_origens_lead_ordem", "crm_origens_lead", ["ordem"])

    # Seed só quando a tabela está vazia (a lista é editável depois).
    total = bind.execute(sa.text("SELECT COUNT(*) FROM crm_origens_lead")).scalar()
    if not total:
        for nome, ordem in SEED:
            bind.execute(
                sa.text(
                    "INSERT INTO crm_origens_lead (nome, ordem, ativo) VALUES (:nome, :ordem, true)"
                ),
                {"nome": nome, "ordem": ordem},
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("crm_origens_lead"):
        op.drop_table("crm_origens_lead")
