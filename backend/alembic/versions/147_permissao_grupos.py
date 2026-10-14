"""Grupos de permissão no lugar do perfil fixo (#S202609-0024).

Revision ID: 147_permissao_grupos
Revises: 146_wpp_figurinha_fav
Create Date: 2026-10-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "147_permissao_grupos"
down_revision = "146_wpp_figurinha_fav"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if insp.has_table("permissao_grupos"):
        return
    op.create_table(
        "permissao_grupos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("sistema", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_permissao_grupos_tenant_slug"),
    )
    op.create_index("ix_permissao_grupos_tenant_id", "permissao_grupos", ["tenant_id"])
    op.create_table(
        "permissao_grupo_itens",
        sa.Column(
            "grupo_id",
            sa.Integer(),
            sa.ForeignKey("permissao_grupos.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("codigo", sa.String(length=40), primary_key=True),
    )
    op.create_table(
        "atendente_permissao_grupo",
        sa.Column(
            "atendente_id",
            sa.Integer(),
            sa.ForeignKey("atendentes.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "grupo_id",
            sa.Integer(),
            sa.ForeignKey("permissao_grupos.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO permissao_grupos (tenant_id, nome, slug, sistema)
            SELECT t.id, v.nome, v.slug, TRUE
            FROM tenants t
            CROSS JOIN (VALUES
                ('Administrador', 'administrador'),
                ('Comercial', 'comercial'),
                ('Operação', 'atendente')
            ) AS v(nome, slug)
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO permissao_grupo_itens (grupo_id, codigo)
            SELECT g.id, c.codigo
            FROM permissao_grupos g
            JOIN (VALUES
                ('administrador', 'admin'),
                ('administrador', 'comercial'),
                ('administrador', 'operacional'),
                ('comercial', 'comercial'),
                ('atendente', 'operacional')
            ) AS c(slug, codigo) ON c.slug = g.slug
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO atendente_permissao_grupo (atendente_id, grupo_id)
            SELECT a.id, g.id
            FROM atendentes a
            JOIN permissao_grupos g
              ON g.tenant_id = a.tenant_id
             AND g.slug = CASE a.role
                    WHEN 'admin' THEN 'administrador'
                    WHEN 'comercial' THEN 'comercial'
                    ELSE 'atendente'
                 END
            WHERE a.role <> 'saas_ops'
            """
        )
    )


def downgrade() -> None:
    op.drop_table("atendente_permissao_grupo")
    op.drop_table("permissao_grupo_itens")
    op.drop_index("ix_permissao_grupos_tenant_id", table_name="permissao_grupos")
    op.drop_table("permissao_grupos")
