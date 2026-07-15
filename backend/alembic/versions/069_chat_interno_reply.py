"""Chat interno: citação (reply) em mensagens (#539).

Revision ID: 069_chat_interno_reply
Revises: 068_func_rede_telefone
Create Date: 2026-07-15
"""

import sqlalchemy as sa
from alembic import op

revision = "069_chat_interno_reply"
down_revision = "068_func_rede_telefone"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("mensagens_internas"):
        return
    cols = [c["name"] for c in insp.get_columns("mensagens_internas")]
    if "reply_to_message_id" not in cols:
        op.add_column(
            "mensagens_internas",
            sa.Column("reply_to_message_id", sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            "fk_mensagens_internas_reply_to",
            "mensagens_internas",
            "mensagens_internas",
            ["reply_to_message_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index(
            "ix_mensagens_internas_reply_to_message_id",
            "mensagens_internas",
            ["reply_to_message_id"],
        )
    if "reply_preview" not in cols:
        op.add_column(
            "mensagens_internas",
            sa.Column("reply_preview", sa.String(length=500), nullable=True),
        )
    if "reply_autor_nome" not in cols:
        op.add_column(
            "mensagens_internas",
            sa.Column("reply_autor_nome", sa.String(length=200), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("mensagens_internas"):
        return
    cols = [c["name"] for c in insp.get_columns("mensagens_internas")]
    fks = {fk["name"] for fk in insp.get_foreign_keys("mensagens_internas")}
    if "fk_mensagens_internas_reply_to" in fks:
        op.drop_constraint("fk_mensagens_internas_reply_to", "mensagens_internas", type_="foreignkey")
    idxs = {ix["name"] for ix in insp.get_indexes("mensagens_internas")}
    if "ix_mensagens_internas_reply_to_message_id" in idxs:
        op.drop_index("ix_mensagens_internas_reply_to_message_id", table_name="mensagens_internas")
    if "reply_autor_nome" in cols:
        op.drop_column("mensagens_internas", "reply_autor_nome")
    if "reply_preview" in cols:
        op.drop_column("mensagens_internas", "reply_preview")
    if "reply_to_message_id" in cols:
        op.drop_column("mensagens_internas", "reply_to_message_id")
