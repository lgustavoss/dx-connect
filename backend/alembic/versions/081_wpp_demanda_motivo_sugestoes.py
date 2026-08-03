"""Decisões de sugestão de motivo a partir de «Outros» nas demandas WA (#594).

Revision ID: 081_wpp_demanda_motivo_sugestoes
Revises: 080_wpp_edicao_apagar
Create Date: 2026-08-02
"""

import sqlalchemy as sa
from alembic import op

revision = "081_wpp_demanda_motivo_sugestoes"
down_revision = "080_wpp_edicao_apagar"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("whatsapp_demanda_motivo_sugestoes"):
        return
    op.create_table(
        "whatsapp_demanda_motivo_sugestoes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "natureza_id",
            sa.Integer(),
            sa.ForeignKey("ticket_naturezas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("texto_normalizado", sa.String(500), nullable=False),
        sa.Column("texto_exemplo", sa.String(500), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column(
            "motivo_criado_id",
            sa.Integer(),
            sa.ForeignKey("ticket_motivos.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "decidido_por_id",
            sa.Integer(),
            sa.ForeignKey("atendentes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "decidido_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "natureza_id",
            "texto_normalizado",
            name="uq_wpp_demanda_motivo_sugestao_nat_texto",
        ),
    )
    op.create_index(
        "ix_wpp_demanda_motivo_sugestoes_natureza_id",
        "whatsapp_demanda_motivo_sugestoes",
        ["natureza_id"],
    )
    op.create_index(
        "ix_wpp_demanda_motivo_sugestoes_status",
        "whatsapp_demanda_motivo_sugestoes",
        ["status"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("whatsapp_demanda_motivo_sugestoes"):
        return
    op.drop_table("whatsapp_demanda_motivo_sugestoes")
