"""Chat interno: conversas, mensagens e leituras (IC-01).

Revision ID: 058_chat_interno
Revises: 057_kb_portal_settings
Create Date: 2026-07-10
"""

import sqlalchemy as sa
from alembic import op

revision = "058_chat_interno"
down_revision = "057_kb_portal_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversas_internas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("setor_id", sa.Integer(), sa.ForeignKey("setores.id", ondelete="CASCADE"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(tipo = 'setor' AND setor_id IS NOT NULL) OR (tipo = 'direta' AND setor_id IS NULL)",
            name="ck_conversas_internas_tipo_setor",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "setor_id", name="uq_conversas_internas_tenant_setor"),
    )
    op.create_index(op.f("ix_conversas_internas_id"), "conversas_internas", ["id"], unique=False)
    op.create_index(op.f("ix_conversas_internas_tenant_id"), "conversas_internas", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_conversas_internas_tipo"), "conversas_internas", ["tipo"], unique=False)
    op.create_index(op.f("ix_conversas_internas_setor_id"), "conversas_internas", ["setor_id"], unique=False)

    op.create_table(
        "conversas_internas_participantes",
        sa.Column("conversa_id", sa.Integer(), sa.ForeignKey("conversas_internas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("atendente_id", sa.Integer(), sa.ForeignKey("atendentes.id", ondelete="CASCADE"), nullable=False),
        sa.PrimaryKeyConstraint("conversa_id", "atendente_id"),
        sa.UniqueConstraint("conversa_id", "atendente_id", name="uq_conversas_internas_participantes"),
    )
    op.create_index(
        op.f("ix_conversas_internas_participantes_atendente_id"),
        "conversas_internas_participantes",
        ["atendente_id"],
        unique=False,
    )

    op.create_table(
        "mensagens_internas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversa_id", sa.Integer(), sa.ForeignKey("conversas_internas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("atendente_id", sa.Integer(), sa.ForeignKey("atendentes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("corpo", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mensagens_internas_id"), "mensagens_internas", ["id"], unique=False)
    op.create_index(op.f("ix_mensagens_internas_conversa_id"), "mensagens_internas", ["conversa_id"], unique=False)
    op.create_index(op.f("ix_mensagens_internas_atendente_id"), "mensagens_internas", ["atendente_id"], unique=False)
    op.create_index(op.f("ix_mensagens_internas_created_at"), "mensagens_internas", ["created_at"], unique=False)
    op.create_index(
        "ix_mensagens_internas_conversa_created",
        "mensagens_internas",
        ["conversa_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "conversas_internas_leituras",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversa_id", sa.Integer(), sa.ForeignKey("conversas_internas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("atendente_id", sa.Integer(), sa.ForeignKey("atendentes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("atendente_id", "conversa_id", name="uq_conversas_internas_leituras"),
    )
    op.create_index(op.f("ix_conversas_internas_leituras_id"), "conversas_internas_leituras", ["id"], unique=False)
    op.create_index(
        op.f("ix_conversas_internas_leituras_conversa_id"),
        "conversas_internas_leituras",
        ["conversa_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_conversas_internas_leituras_atendente_id"),
        "conversas_internas_leituras",
        ["atendente_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_conversas_internas_leituras_atendente_id"), table_name="conversas_internas_leituras")
    op.drop_index(op.f("ix_conversas_internas_leituras_conversa_id"), table_name="conversas_internas_leituras")
    op.drop_index(op.f("ix_conversas_internas_leituras_id"), table_name="conversas_internas_leituras")
    op.drop_table("conversas_internas_leituras")

    op.drop_index("ix_mensagens_internas_conversa_created", table_name="mensagens_internas")
    op.drop_index(op.f("ix_mensagens_internas_created_at"), table_name="mensagens_internas")
    op.drop_index(op.f("ix_mensagens_internas_atendente_id"), table_name="mensagens_internas")
    op.drop_index(op.f("ix_mensagens_internas_conversa_id"), table_name="mensagens_internas")
    op.drop_index(op.f("ix_mensagens_internas_id"), table_name="mensagens_internas")
    op.drop_table("mensagens_internas")

    op.drop_index(
        op.f("ix_conversas_internas_participantes_atendente_id"),
        table_name="conversas_internas_participantes",
    )
    op.drop_table("conversas_internas_participantes")

    op.drop_index(op.f("ix_conversas_internas_setor_id"), table_name="conversas_internas")
    op.drop_index(op.f("ix_conversas_internas_tipo"), table_name="conversas_internas")
    op.drop_index(op.f("ix_conversas_internas_tenant_id"), table_name="conversas_internas")
    op.drop_index(op.f("ix_conversas_internas_id"), table_name="conversas_internas")
    op.drop_table("conversas_internas")
