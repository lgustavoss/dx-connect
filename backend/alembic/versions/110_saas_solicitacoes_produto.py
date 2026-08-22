"""Fila SaaS de solicitações de produto + token de ingest (#855).

Revision ID: 110_saas_solicitacoes_produto
Revises: 109_ponto_geofence
Create Date: 2026-08-22
"""

import sqlalchemy as sa
from alembic import op

revision = "110_saas_solicitacoes_produto"
down_revision = "109_ponto_geofence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("clientes_saas"):
        cols = {c["name"] for c in insp.get_columns("clientes_saas")}
        if "ingest_token_hash" not in cols:
            op.add_column(
                "clientes_saas",
                sa.Column("ingest_token_hash", sa.String(64), nullable=True),
            )

    if not insp.has_table("saas_solicitacoes_produto"):
        op.create_table(
            "saas_solicitacoes_produto",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "cliente_saas_id",
                sa.Integer(),
                sa.ForeignKey("clientes_saas.id", ondelete="SET NULL"),
                nullable=True,
                index=True,
            ),
            sa.Column("instance_slug", sa.String(80), nullable=False, index=True),
            sa.Column("origem_solicitacao_id", sa.Integer(), nullable=False),
            sa.Column("tipo", sa.String(32), nullable=False, index=True),
            sa.Column("titulo", sa.String(200), nullable=False),
            sa.Column("descricao", sa.Text(), nullable=False),
            sa.Column(
                "status",
                sa.String(40),
                nullable=False,
                server_default="aberta",
                index=True,
            ),
            sa.Column("versao_contexto", sa.String(64), nullable=True),
            sa.Column("autor_nome", sa.String(255), nullable=True),
            sa.Column("created_at_origem", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "ingested_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint(
                "instance_slug",
                "origem_solicitacao_id",
                name="uq_saas_solicitacoes_produto_origem",
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("saas_solicitacoes_produto"):
        op.drop_table("saas_solicitacoes_produto")
    if insp.has_table("clientes_saas"):
        cols = {c["name"] for c in insp.get_columns("clientes_saas")}
        if "ingest_token_hash" in cols:
            op.drop_column("clientes_saas", "ingest_token_hash")
