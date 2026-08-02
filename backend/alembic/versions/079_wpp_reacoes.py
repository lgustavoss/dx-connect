"""WhatsApp: reações em mensagens do chat com o cliente (#630 lote 2).

Revision ID: 079_wpp_reacoes
Revises: 078_wpp_foto_perfil
Create Date: 2026-08-01
"""

import sqlalchemy as sa
from alembic import op

revision = "079_wpp_reacoes"
down_revision = "078_wpp_foto_perfil"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("whatsapp_mensagens"):
        return
    if insp.has_table("whatsapp_mensagem_reacoes"):
        return
    op.create_table(
        "whatsapp_mensagem_reacoes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "mensagem_id",
            sa.Integer(),
            sa.ForeignKey("whatsapp_mensagens.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("origem", sa.String(20), nullable=False),
        sa.Column("emoji", sa.String(16), nullable=False),
        sa.Column(
            "atendente_id",
            sa.Integer(),
            sa.ForeignKey("atendentes.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("mensagem_id", "origem", name="uq_whatsapp_mensagem_reacoes_mensagem_origem"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("whatsapp_mensagem_reacoes"):
        op.drop_table("whatsapp_mensagem_reacoes")
