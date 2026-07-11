"""Chat interno: grupos personalizados e papel de participante.

Revision ID: 063_chat_interno_grupos
Revises: 062_chat_interno_ocultacao
Create Date: 2026-07-11
"""

import sqlalchemy as sa
from alembic import op

revision = "063_chat_interno_grupos"
down_revision = "062_chat_interno_ocultacao"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("conversas_internas", sa.Column("titulo", sa.String(length=120), nullable=True))
    op.add_column(
        "conversas_internas_participantes",
        sa.Column("papel", sa.String(length=20), server_default="membro", nullable=False),
    )
    op.drop_constraint("ck_conversas_internas_tipo_setor", "conversas_internas", type_="check")
    op.create_check_constraint(
        "ck_conversas_internas_tipo_setor",
        "conversas_internas",
        "(tipo = 'setor' AND setor_id IS NOT NULL) OR (tipo IN ('direta', 'grupo') AND setor_id IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_conversas_internas_tipo_setor", "conversas_internas", type_="check")
    op.create_check_constraint(
        "ck_conversas_internas_tipo_setor",
        "conversas_internas",
        "(tipo = 'setor' AND setor_id IS NOT NULL) OR (tipo = 'direta' AND setor_id IS NULL)",
    )
    op.drop_column("conversas_internas_participantes", "papel")
    op.drop_column("conversas_internas", "titulo")
