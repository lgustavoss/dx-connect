"""Catálogo comercial saas_planos / saas_modulos + plano_id em clientes_saas.

Revision ID: 091_saas_planos
Revises: 090_saas_entrega
Create Date: 2026-08-10
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "091_saas_planos"
down_revision = "090_saas_entrega"
branch_labels = None
depends_on = None

_MODULOS_SEED = (
    ("helpdesk", "Helpdesk / tickets", "Tickets e atendimento helpdesk"),
    ("whatsapp", "WhatsApp", "Canal WhatsApp / Evolution"),
    ("contratos", "Contratos", "Módulo de contratos comerciais"),
    ("boletos", "Boletos", "Emissão e gestão de boletos"),
)

_PLANOS_SEED = (
    ("trial", "Trial", "Plano de avaliação", 10, ("helpdesk",)),
    (
        "profissional",
        "Profissional",
        "Plano padrão com canais e módulos comerciais",
        20,
        ("helpdesk", "whatsapp", "contratos", "boletos"),
    ),
    (
        "enterprise",
        "Enterprise",
        "Plano completo (catálogo comercial; ops pode diferenciar depois)",
        30,
        ("helpdesk", "whatsapp", "contratos", "boletos"),
    ),
)


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("saas_modulos"):
        op.create_table(
            "saas_modulos",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("codigo", sa.String(80), nullable=False),
            sa.Column("nome", sa.String(120), nullable=False),
            sa.Column("descricao", sa.Text(), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("codigo", name="uq_saas_modulos_codigo"),
        )
        op.create_index("ix_saas_modulos_codigo", "saas_modulos", ["codigo"])

    if not insp.has_table("saas_planos"):
        op.create_table(
            "saas_planos",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("codigo", sa.String(80), nullable=False),
            sa.Column("nome", sa.String(120), nullable=False),
            sa.Column("descricao", sa.Text(), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("codigo", name="uq_saas_planos_codigo"),
        )
        op.create_index("ix_saas_planos_codigo", "saas_planos", ["codigo"])

    if not insp.has_table("saas_plano_modulos"):
        op.create_table(
            "saas_plano_modulos",
            sa.Column("plano_id", sa.Integer(), sa.ForeignKey("saas_planos.id", ondelete="CASCADE"), primary_key=True),
            sa.Column(
                "modulo_id", sa.Integer(), sa.ForeignKey("saas_modulos.id", ondelete="CASCADE"), primary_key=True
            ),
            sa.UniqueConstraint("plano_id", "modulo_id", name="uq_saas_plano_modulo"),
        )

    # Seed idempotente
    modulos = sa.table(
        "saas_modulos",
        sa.column("id", sa.Integer),
        sa.column("codigo", sa.String),
        sa.column("nome", sa.String),
        sa.column("descricao", sa.Text),
        sa.column("ativo", sa.Boolean),
    )
    planos = sa.table(
        "saas_planos",
        sa.column("id", sa.Integer),
        sa.column("codigo", sa.String),
        sa.column("nome", sa.String),
        sa.column("descricao", sa.Text),
        sa.column("ativo", sa.Boolean),
        sa.column("ordem", sa.Integer),
    )
    links = sa.table(
        "saas_plano_modulos",
        sa.column("plano_id", sa.Integer),
        sa.column("modulo_id", sa.Integer),
    )

    existing_mod = {r[0] for r in bind.execute(sa.select(modulos.c.codigo)).fetchall()}
    for codigo, nome, descricao in _MODULOS_SEED:
        if codigo not in existing_mod:
            bind.execute(
                modulos.insert().values(codigo=codigo, nome=nome, descricao=descricao, ativo=True)
            )

    mod_ids = {r[0]: r[1] for r in bind.execute(sa.select(modulos.c.codigo, modulos.c.id)).fetchall()}

    existing_plan = {r[0] for r in bind.execute(sa.select(planos.c.codigo)).fetchall()}
    for codigo, nome, descricao, ordem, mod_codigos in _PLANOS_SEED:
        if codigo not in existing_plan:
            bind.execute(
                planos.insert().values(
                    codigo=codigo, nome=nome, descricao=descricao, ativo=True, ordem=ordem
                )
            )

    plan_ids = {r[0]: r[1] for r in bind.execute(sa.select(planos.c.codigo, planos.c.id)).fetchall()}
    existing_links = {
        (r[0], r[1]) for r in bind.execute(sa.select(links.c.plano_id, links.c.modulo_id)).fetchall()
    }
    for codigo, _nome, _desc, _ordem, mod_codigos in _PLANOS_SEED:
        pid = plan_ids.get(codigo)
        if pid is None:
            continue
        for mc in mod_codigos:
            mid = mod_ids.get(mc)
            if mid is None or (pid, mid) in existing_links:
                continue
            bind.execute(links.insert().values(plano_id=pid, modulo_id=mid))
            existing_links.add((pid, mid))

    if insp.has_table("clientes_saas"):
        cols = {c["name"] for c in insp.get_columns("clientes_saas")}
        if "plano_id" not in cols:
            op.add_column("clientes_saas", sa.Column("plano_id", sa.Integer(), nullable=True))
            op.create_foreign_key(
                "fk_clientes_saas_plano_id",
                "clientes_saas",
                "saas_planos",
                ["plano_id"],
                ["id"],
                ondelete="SET NULL",
            )
            op.create_index("ix_clientes_saas_plano_id", "clientes_saas", ["plano_id"])

        # Backfill best-effort: texto plano → plano_id por codigo ou nome
        clientes = sa.table(
            "clientes_saas",
            sa.column("id", sa.Integer),
            sa.column("plano", sa.String),
            sa.column("plano_id", sa.Integer),
        )
        plan_by_codigo = {
            r[0].lower(): r[1] for r in bind.execute(sa.select(planos.c.codigo, planos.c.id)).fetchall()
        }
        plan_by_nome = {
            r[0].lower(): r[1] for r in bind.execute(sa.select(planos.c.nome, planos.c.id)).fetchall()
        }
        rows = bind.execute(
            sa.select(clientes.c.id, clientes.c.plano, clientes.c.plano_id).where(
                clientes.c.plano.isnot(None), clientes.c.plano_id.is_(None)
            )
        ).fetchall()
        for cid, plano_txt, _ in rows:
            key = (plano_txt or "").strip().lower()
            if not key:
                continue
            pid = plan_by_codigo.get(key) or plan_by_nome.get(key)
            if pid is None:
                continue
            nome = None
            for codigo, n, *_rest in _PLANOS_SEED:
                if plan_ids.get(codigo) == pid:
                    nome = n
                    break
            vals: dict = {"plano_id": pid}
            if nome:
                vals["plano"] = nome
            bind.execute(clientes.update().where(clientes.c.id == cid).values(**vals))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("clientes_saas"):
        cols = {c["name"] for c in insp.get_columns("clientes_saas")}
        if "plano_id" in cols:
            try:
                op.drop_constraint("fk_clientes_saas_plano_id", "clientes_saas", type_="foreignkey")
            except Exception:
                pass
            try:
                op.drop_index("ix_clientes_saas_plano_id", table_name="clientes_saas")
            except Exception:
                pass
            op.drop_column("clientes_saas", "plano_id")
    if insp.has_table("saas_plano_modulos"):
        op.drop_table("saas_plano_modulos")
    if insp.has_table("saas_planos"):
        op.drop_index("ix_saas_planos_codigo", table_name="saas_planos")
        op.drop_table("saas_planos")
    if insp.has_table("saas_modulos"):
        op.drop_index("ix_saas_modulos_codigo", table_name="saas_modulos")
        op.drop_table("saas_modulos")
