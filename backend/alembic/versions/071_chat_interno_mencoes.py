"""Chat interno: menções (@user / @all) em mensagens.

Revision ID: 071_chat_interno_mencoes
Revises: 070_presenca_token
Create Date: 2026-07-16
"""

import sqlalchemy as sa
from alembic import op

revision = "071_chat_interno_mencoes"
down_revision = "070_presenca_token"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("mensagens_internas"):
        return
    cols = {c["name"] for c in insp.get_columns("mensagens_internas")}
    if "mencoes" not in cols:
        op.add_column("mensagens_internas", sa.Column("mencoes", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("mensagens_internas"):
        return
    cols = {c["name"] for c in insp.get_columns("mensagens_internas")}
    if "mencoes" in cols:
        op.drop_column("mensagens_internas", "mencoes")
