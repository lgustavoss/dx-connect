"""Preço por módulo + usuários inclusos / extra nos planos.

Revision ID: 122_saas_preco_modulos
Revises: 121_saas_catalogo_precos
Create Date: 2026-08-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "122_saas_preco_modulos"
down_revision = "121_saas_catalogo_precos"
branch_labels = None
depends_on = None

# Preços unitários (R$/mês) — Essencial≈97, Profissional≈197, Enterprise≈347
_PRECOS_MODULO = {
    "helpdesk": 29,
    "whatsapp": 29,
    "email": 15,
    "portal": 12,
    "kb": 12,
    "chat-interno": 20,
    "crm": 25,
    "contratos": 20,
    "sla": 20,
    "pdv": 15,
    "ponto": 40,
    "faturamento": 40,
    "boletos": 35,
    "mobile": 35,
}


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("saas_modulos") or not insp.has_table("saas_planos"):
        return

    mod_cols = {c["name"] for c in insp.get_columns("saas_modulos")}
    if "preco_mensal" not in mod_cols:
        op.add_column(
            "saas_modulos",
            sa.Column("preco_mensal", sa.Numeric(12, 2), nullable=True),
        )

    plan_cols = {c["name"] for c in insp.get_columns("saas_planos")}
    if "usuarios_inclusos" not in plan_cols:
        op.add_column(
            "saas_planos",
            sa.Column("usuarios_inclusos", sa.Integer(), nullable=False, server_default="3"),
        )
    if "preco_usuario_extra" not in plan_cols:
        op.add_column(
            "saas_planos",
            sa.Column("preco_usuario_extra", sa.Numeric(12, 2), nullable=True, server_default="10"),
        )

    for codigo, preco in _PRECOS_MODULO.items():
        bind.execute(
            sa.text(
                "UPDATE saas_modulos SET preco_mensal = :preco, updated_at = now() "
                "WHERE codigo = :codigo"
            ),
            {"codigo": codigo, "preco": preco},
        )

    bind.execute(
        sa.text(
            """
            UPDATE saas_planos SET
                usuarios_inclusos = 3,
                preco_usuario_extra = 10,
                max_postos = NULL,
                max_usuarios = NULL,
                updated_at = now()
            """
        )
    )

    # Recalcula preco_mensal do plano = soma dos módulos ligados
    rows = bind.execute(
        sa.text(
            """
            SELECT p.id, COALESCE(SUM(m.preco_mensal), 0) AS total
            FROM saas_planos p
            LEFT JOIN saas_plano_modulos pm ON pm.plano_id = p.id
            LEFT JOIN saas_modulos m ON m.id = pm.modulo_id
            GROUP BY p.id
            """
        )
    ).fetchall()
    for pid, total in rows:
        bind.execute(
            sa.text(
                "UPDATE saas_planos SET preco_mensal = :total, updated_at = now() WHERE id = :pid"
            ),
            {"pid": pid, "total": total},
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("saas_planos"):
        cols = {c["name"] for c in insp.get_columns("saas_planos")}
        if "preco_usuario_extra" in cols:
            op.drop_column("saas_planos", "preco_usuario_extra")
        if "usuarios_inclusos" in cols:
            op.drop_column("saas_planos", "usuarios_inclusos")
    if insp.has_table("saas_modulos"):
        cols = {c["name"] for c in insp.get_columns("saas_modulos")}
        if "preco_mensal" in cols:
            op.drop_column("saas_modulos", "preco_mensal")
