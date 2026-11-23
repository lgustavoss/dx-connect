"""Vínculo N:N entre contato e rede (#1407).

Aditiva: cria `funcionario_rede_vinculo` e faz o backfill do vínculo 1:1 atual
(sócio → `rede_id`; supervisor → redes das empresas em `funcionario_rede_empresa`;
colaborador → rede da `empresa_id`). O backfill é idempotente — pode rodar de novo
sem duplicar (NOT EXISTS + unique por funcionário/rede). A coluna legada
`funcionarios_rede.rede_id` permanece por um release.

Revision ID: 163_funcionario_rede_vinculo
Revises: 162_titulo_multa
Create Date: 2026-11-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "163_funcionario_rede_vinculo"
down_revision = "162_titulo_multa"
branch_labels = None
depends_on = None

TABELA = "funcionario_rede_vinculo"

_BACKFILL_SOCIO = """
INSERT INTO funcionario_rede_vinculo (funcionario_id, rede_id)
SELECT f.id, f.rede_id
FROM funcionarios_rede f
WHERE f.rede_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM funcionario_rede_vinculo v
      WHERE v.funcionario_id = f.id
        AND v.rede_id = f.rede_id
  )
"""

_BACKFILL_SUPERVISOR = """
INSERT INTO funcionario_rede_vinculo (funcionario_id, rede_id)
SELECT DISTINCT f.id, e.rede_id
FROM funcionarios_rede f
JOIN funcionario_rede_empresa fe ON fe.funcionario_id = f.id
JOIN empresas e ON e.id = fe.empresa_id
WHERE e.rede_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM funcionario_rede_vinculo v
      WHERE v.funcionario_id = f.id
        AND v.rede_id = e.rede_id
  )
"""

_BACKFILL_COLABORADOR = """
INSERT INTO funcionario_rede_vinculo (funcionario_id, rede_id)
SELECT DISTINCT f.id, e.rede_id
FROM funcionarios_rede f
JOIN empresas e ON e.id = f.empresa_id
WHERE f.empresa_id IS NOT NULL
  AND e.rede_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM funcionario_rede_vinculo v
      WHERE v.funcionario_id = f.id
        AND v.rede_id = e.rede_id
  )
"""


def _backfill(bind: sa.engine.Connection) -> None:
    for sql in (_BACKFILL_SOCIO, _BACKFILL_SUPERVISOR, _BACKFILL_COLABORADOR):
        bind.execute(sa.text(sql))


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table(TABELA):
        op.create_table(
            TABELA,
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "funcionario_id",
                sa.Integer(),
                sa.ForeignKey("funcionarios_rede.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "rede_id",
                sa.Integer(),
                sa.ForeignKey("redes.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.UniqueConstraint("funcionario_id", "rede_id", name="uq_funcionario_rede_vinculo"),
        )
        op.create_index(
            "ix_funcionario_rede_vinculo_funcionario_id",
            TABELA,
            ["funcionario_id"],
        )
        op.create_index(
            "ix_funcionario_rede_vinculo_rede_id",
            TABELA,
            ["rede_id"],
        )
    _backfill(bind)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table(TABELA):
        op.drop_table(TABELA)
