"""Portal funcionário: senha e preferências de acesso (#300/#303).

Revision ID: 075_portal_funcionario_auth
Revises: 074_wpp_classificacao_demanda
Create Date: 2026-07-19
"""

import sqlalchemy as sa
from alembic import op

revision = "075_portal_funcionario_auth"
down_revision = "074_wpp_classificacao_demanda"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("funcionarios_rede"):
        return
    cols = {c["name"] for c in insp.get_columns("funcionarios_rede")}
    if "senha_hash" not in cols:
        op.add_column("funcionarios_rede", sa.Column("senha_hash", sa.String(255), nullable=True))
    if "must_change_password" not in cols:
        op.add_column(
            "funcionarios_rede",
            sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    if "token_version" not in cols:
        op.add_column(
            "funcionarios_rede",
            sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
        )
    if "notificar_email_portal" not in cols:
        op.add_column(
            "funcionarios_rede",
            sa.Column("notificar_email_portal", sa.Boolean(), nullable=False, server_default=sa.true()),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("funcionarios_rede"):
        return
    cols = {c["name"] for c in insp.get_columns("funcionarios_rede")}
    for col in ("notificar_email_portal", "token_version", "must_change_password", "senha_hash"):
        if col in cols:
            op.drop_column("funcionarios_rede", col)
