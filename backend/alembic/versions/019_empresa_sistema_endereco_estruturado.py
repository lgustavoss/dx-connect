"""empresa_sistema: endereco estruturado; remove coluna ativo.

Revision ID: 019_empresa_endereco
Revises: 018_sys_logo
Create Date: 2026-05-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "019_empresa_endereco"
down_revision = "018_sys_logo"
branch_labels = None
depends_on = None


def _has_column(insp, table: str, column: str) -> bool:
    try:
        cols = insp.get_columns(table)
    except Exception:
        return False
    return any(c.get("name") == column for c in cols)


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if not insp.has_table("empresa_sistema"):
        return

    if not _has_column(insp, "empresa_sistema", "numero"):
        op.add_column("empresa_sistema", sa.Column("numero", sa.String(length=20), nullable=True))
    if not _has_column(insp, "empresa_sistema", "complemento"):
        op.add_column("empresa_sistema", sa.Column("complemento", sa.String(length=100), nullable=True))
    if not _has_column(insp, "empresa_sistema", "bairro"):
        op.add_column("empresa_sistema", sa.Column("bairro", sa.String(length=100), nullable=True))
    if not _has_column(insp, "empresa_sistema", "cidade"):
        op.add_column("empresa_sistema", sa.Column("cidade", sa.String(length=100), nullable=True))
    if not _has_column(insp, "empresa_sistema", "estado"):
        op.add_column("empresa_sistema", sa.Column("estado", sa.String(length=2), nullable=True))
    if not _has_column(insp, "empresa_sistema", "cep"):
        op.add_column("empresa_sistema", sa.Column("cep", sa.String(length=10), nullable=True))

    if _has_column(insp, "empresa_sistema", "ativo"):
        op.drop_column("empresa_sistema", "ativo")


def downgrade() -> None:
    bind = op.get_bind()
    if not inspect(bind).has_table("empresa_sistema"):
        return

    if not _has_column(inspect(bind), "empresa_sistema", "ativo"):
        op.add_column(
            "empresa_sistema",
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        )

    for col in ("cep", "estado", "cidade", "bairro", "complemento", "numero"):
        if _has_column(inspect(bind), "empresa_sistema", col):
            op.drop_column("empresa_sistema", col)
