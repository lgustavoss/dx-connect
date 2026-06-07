"""funcionario escopo_empresas (all | selected)

Revision ID: 034_funcionario_escopo
Revises: 033_ticket_rede_id
Create Date: 2026-06-06

"""

from alembic import op
import sqlalchemy as sa

revision = "034_funcionario_escopo"
down_revision = "033_ticket_rede_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "funcionarios_rede",
        sa.Column("escopo_empresas", sa.String(20), nullable=False, server_default="selected"),
    )
    op.execute(
        """
        UPDATE funcionarios_rede
        SET escopo_empresas = 'all'
        WHERE tipo = 'socio'
        """
    )
    # Colaboradores: garantir vínculo na tabela N:N para consultas unificadas
    op.execute(
        """
        INSERT INTO funcionario_rede_empresa (funcionario_id, empresa_id)
        SELECT f.id, f.empresa_id
        FROM funcionarios_rede f
        WHERE f.tipo = 'colaborador'
          AND f.empresa_id IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM funcionario_rede_empresa fre
            WHERE fre.funcionario_id = f.id AND fre.empresa_id = f.empresa_id
          )
        """
    )


def downgrade() -> None:
    op.drop_column("funcionarios_rede", "escopo_empresas")
