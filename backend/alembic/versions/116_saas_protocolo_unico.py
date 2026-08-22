"""Protocolo #S único no control-plane (não por instância).

Revision ID: 116_saas_protocolo_unico
Revises: 115_solicitacao_protocolo
Create Date: 2026-08-22
"""

import sqlalchemy as sa
from alembic import op

revision = "116_saas_protocolo_unico"
down_revision = "115_solicitacao_protocolo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("solicitacoes_melhoria"):
        cols = {c["name"] for c in insp.get_columns("solicitacoes_melhoria")}
        if "protocolo" in cols:
            op.alter_column(
                "solicitacoes_melhoria",
                "protocolo",
                existing_type=sa.String(32),
                nullable=True,
            )

    if not insp.has_table("saas_solicitacoes_produto"):
        return

    uqs = {u["name"] for u in insp.get_unique_constraints("saas_solicitacoes_produto")}
    if "uq_saas_solicitacoes_produto_protocolo" in uqs:
        op.drop_constraint(
            "uq_saas_solicitacoes_produto_protocolo",
            "saas_solicitacoes_produto",
            type_="unique",
        )

    dialect = bind.dialect.name
    if dialect == "postgresql":
        op.execute(
            sa.text(
                """
                DO $$
                DECLARE
                  yyyymm text;
                  n int := 0;
                  r record;
                BEGIN
                  yyyymm := to_char(timezone('America/Sao_Paulo', now()), 'YYYYMM');
                  UPDATE saas_solicitacoes_produto SET protocolo = NULL;
                  FOR r IN SELECT id FROM saas_solicitacoes_produto ORDER BY id LOOP
                    n := n + 1;
                    UPDATE saas_solicitacoes_produto
                    SET protocolo = '#S' || yyyymm || '-' || lpad(n::text, 4, '0')
                    WHERE id = r.id;
                  END LOOP;
                  INSERT INTO protocol_sequences (kind, ano_mes, last_value)
                  VALUES ('S', yyyymm, n)
                  ON CONFLICT (kind, ano_mes) DO UPDATE SET last_value = EXCLUDED.last_value;
                END $$;
                """
            )
        )
        op.execute(
            sa.text(
                """
                UPDATE solicitacoes_melhoria m
                SET protocolo = s.protocolo
                FROM saas_solicitacoes_produto s
                WHERE s.origem_solicitacao_id = m.id
                  AND NOT EXISTS (
                    SELECT 1 FROM saas_solicitacoes_produto o
                    WHERE o.origem_solicitacao_id = m.id AND o.id <> s.id
                  )
                """
            )
        )

    op.create_unique_constraint(
        "uq_saas_solicitacoes_produto_protocolo",
        "saas_solicitacoes_produto",
        ["protocolo"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("saas_solicitacoes_produto"):
        uqs = {u["name"] for u in insp.get_unique_constraints("saas_solicitacoes_produto")}
        if "uq_saas_solicitacoes_produto_protocolo" in uqs:
            op.drop_constraint(
                "uq_saas_solicitacoes_produto_protocolo",
                "saas_solicitacoes_produto",
                type_="unique",
            )
            op.create_unique_constraint(
                "uq_saas_solicitacoes_produto_protocolo",
                "saas_solicitacoes_produto",
                ["instance_slug", "protocolo"],
            )
    if insp.has_table("solicitacoes_melhoria"):
        cols = {c["name"] for c in insp.get_columns("solicitacoes_melhoria")}
        if "protocolo" in cols:
            op.alter_column(
                "solicitacoes_melhoria",
                "protocolo",
                existing_type=sa.String(32),
                nullable=False,
            )
