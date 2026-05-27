"""protocol_sequences: chave mensal YYYYMM (sem hífen na data).

Revision ID: 018_protocol_sequences_yyyymm
Revises: 017_protocol_sequences
Create Date: 2026-05-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision = "018_protocol_sequences_yyyymm"
down_revision = "017_protocol_sequences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("protocol_sequences"):
        return
    # Legado: chave era YYYY-MM; protocolo exibido #T2026-05-0001 → passa a #T202605-0001.
    # Se já existir linha YYYYMM e outra YYYY-MM para o mesmo kind, fundir last_value e apagar a legada.
    op.execute(
        text(
            """
        UPDATE protocol_sequences AS d
        SET last_value = GREATEST(d.last_value, s.last_value)
        FROM protocol_sequences AS s
        WHERE s.ano_mes LIKE '%-%'
          AND d.kind = s.kind
          AND d.ano_mes = replace(s.ano_mes, '-', '')
        """
        )
    )
    op.execute(
        text(
            """
        DELETE FROM protocol_sequences AS s
        WHERE s.ano_mes LIKE '%-%'
          AND EXISTS (
            SELECT 1 FROM protocol_sequences AS d
            WHERE d.kind = s.kind AND d.ano_mes = replace(s.ano_mes, '-', '')
          )
        """
        )
    )
    op.execute(
        text(
            """
        UPDATE protocol_sequences
        SET ano_mes = replace(ano_mes, '-', '')
        WHERE ano_mes LIKE '%-%'
        """
        )
    )
    op.alter_column(
        "protocol_sequences",
        "ano_mes",
        existing_type=sa.String(length=7),
        type_=sa.String(length=6),
        existing_nullable=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("protocol_sequences"):
        return
    op.alter_column(
        "protocol_sequences",
        "ano_mes",
        existing_type=sa.String(length=6),
        type_=sa.String(length=7),
        existing_nullable=False,
    )
    op.execute(
        text(
            """
        UPDATE protocol_sequences
        SET ano_mes = substr(ano_mes, 1, 4) || '-' || substr(ano_mes, 5, 2)
        WHERE length(ano_mes) = 6 AND ano_mes NOT LIKE '%-%'
        """
        )
    )
