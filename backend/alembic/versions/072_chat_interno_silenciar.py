"""Chat interno: silenciar conversa por participante (grupos).

Revision ID: 072_chat_interno_silenciar
Revises: 071_chat_interno_mencoes
Create Date: 2026-07-17
"""

import sqlalchemy as sa
from alembic import op

revision = "072_chat_interno_silenciar"
down_revision = "071_chat_interno_mencoes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("conversas_internas_participantes"):
        return
    cols = {c["name"] for c in insp.get_columns("conversas_internas_participantes")}
    if "silenciado_em" not in cols:
        op.add_column(
            "conversas_internas_participantes",
            sa.Column("silenciado_em", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("conversas_internas_participantes"):
        return
    cols = {c["name"] for c in insp.get_columns("conversas_internas_participantes")}
    if "silenciado_em" in cols:
        op.drop_column("conversas_internas_participantes", "silenciado_em")
