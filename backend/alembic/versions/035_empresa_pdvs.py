"""PDVs por empresa + catálogos globais

Revision ID: 035_empresa_pdvs
Revises: 034_funcionario_escopo
Create Date: 2026-06-06

"""

from alembic import op
import sqlalchemy as sa

revision = "035_empresa_pdvs"
down_revision = "034_funcionario_escopo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pdv_rotulos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("ordem_exibicao", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "pdv_tipos_acesso_remoto",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("ordem_exibicao", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "empresa_pdvs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("codigo", sa.String(32), nullable=False),
        sa.Column("rotulo_id", sa.Integer(), sa.ForeignKey("pdv_rotulos.id"), nullable=False),
        sa.Column("papel", sa.String(20), nullable=False),
        sa.Column("usa_tef", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tipo_acesso_remoto_id", sa.Integer(), sa.ForeignKey("pdv_tipos_acesso_remoto.id"), nullable=True),
        sa.Column("acesso_remoto_id", sa.String(255), nullable=True),
        sa.Column("acesso_remoto_senha_cifrada", sa.Text(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("empresa_id", "codigo", name="uq_empresa_pdv_codigo"),
    )
    op.create_index("ix_empresa_pdvs_empresa_id", "empresa_pdvs", ["empresa_id"])


def downgrade() -> None:
    op.drop_index("ix_empresa_pdvs_empresa_id", table_name="empresa_pdvs")
    op.drop_table("empresa_pdvs")
    op.drop_table("pdv_tipos_acesso_remoto")
    op.drop_table("pdv_rotulos")
