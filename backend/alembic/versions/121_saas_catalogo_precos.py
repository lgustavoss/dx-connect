"""Catálogo comercial ampliado: módulos do produto + planos com preço e max_usuários.

Revision ID: 121_saas_catalogo_precos
Revises: 120_saas_setores_ops
Create Date: 2026-08-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "121_saas_catalogo_precos"
down_revision = "120_saas_setores_ops"
branch_labels = None
depends_on = None

# (codigo, nome, descricao)
_MODULOS = (
    ("helpdesk", "Helpdesk / tickets", "Tickets e atendimento helpdesk"),
    ("whatsapp", "WhatsApp", "Canal WhatsApp / Evolution"),
    ("contratos", "Contratos comerciais", "Contratos comerciais (parte do CRM)"),
    ("boletos", "Boletos / cobrança", "Emissão e gestão de boletos no fluxo de cobrança"),
    ("email", "Canal e-mail", "Atendimento e tickets por e-mail"),
    ("portal", "Portal do posto", "Portal para funcionários da rede / posto"),
    ("kb", "Base de conhecimento", "Artigos de ajuda e consulta"),
    ("chat-interno", "Chat interno", "Chat entre a equipe da instância"),
    ("crm", "CRM / funil / propostas", "Funil comercial, leads e propostas"),
    ("faturamento", "Faturamento interno", "Faturas internas e fluxo NFS-e"),
    ("ponto", "Ponto eletrônico", "Batidas, escala e ponto da equipe"),
    ("sla", "SLA", "Políticas e calendários de SLA"),
    ("pdv", "Cadastros PDV", "Catálogos e cadastros de PDV / postos"),
    ("mobile", "App mobile", "App Android (APK) do painel"),
)

# (codigo, nome, descricao, ordem, preco_mensal, max_usuarios, modulos)
_PLANOS = (
    (
        "trial",
        "Trial",
        "Avaliação — helpdesk e WhatsApp",
        10,
        0,
        3,
        ("helpdesk", "whatsapp"),
    ),
    (
        "essencial",
        "Essencial",
        "Atendimento omnichannel essencial (tickets, WhatsApp, e-mail, portal e KB)",
        20,
        397,
        8,
        ("helpdesk", "whatsapp", "email", "portal", "kb"),
    ),
    (
        "profissional",
        "Profissional",
        "Operação completa com CRM, chat interno, SLA e PDV",
        30,
        797,
        20,
        (
            "helpdesk",
            "whatsapp",
            "email",
            "portal",
            "kb",
            "chat-interno",
            "crm",
            "contratos",
            "sla",
            "pdv",
        ),
    ),
    (
        "enterprise",
        "Enterprise",
        "Pacote completo — ponto, faturamento, boletos e app mobile",
        40,
        1497,
        50,
        (
            "helpdesk",
            "whatsapp",
            "email",
            "portal",
            "kb",
            "chat-interno",
            "crm",
            "contratos",
            "sla",
            "pdv",
            "ponto",
            "faturamento",
            "boletos",
            "mobile",
        ),
    ),
)


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("saas_modulos") or not insp.has_table("saas_planos"):
        return

    for codigo, nome, descricao in _MODULOS:
        bind.execute(
            sa.text(
                """
                INSERT INTO saas_modulos (codigo, nome, descricao, ativo)
                VALUES (:codigo, :nome, :descricao, true)
                ON CONFLICT ON CONSTRAINT uq_saas_modulos_codigo DO UPDATE SET
                    nome = EXCLUDED.nome,
                    descricao = EXCLUDED.descricao,
                    ativo = true,
                    updated_at = now()
                """
            ),
            {"codigo": codigo, "nome": nome, "descricao": descricao},
        )

    for codigo, nome, descricao, ordem, preco, max_usuarios, _mods in _PLANOS:
        bind.execute(
            sa.text(
                """
                INSERT INTO saas_planos (
                    codigo, nome, descricao, ativo, ordem,
                    preco_mensal, max_postos, max_usuarios
                )
                VALUES (
                    :codigo, :nome, :descricao, true, :ordem,
                    :preco, NULL, :max_usuarios
                )
                ON CONFLICT ON CONSTRAINT uq_saas_planos_codigo DO UPDATE SET
                    nome = EXCLUDED.nome,
                    descricao = EXCLUDED.descricao,
                    ativo = true,
                    ordem = EXCLUDED.ordem,
                    preco_mensal = EXCLUDED.preco_mensal,
                    max_postos = NULL,
                    max_usuarios = EXCLUDED.max_usuarios,
                    updated_at = now()
                """
            ),
            {
                "codigo": codigo,
                "nome": nome,
                "descricao": descricao,
                "ordem": ordem,
                "preco": preco,
                "max_usuarios": max_usuarios,
            },
        )

    mod_ids = {
        row[0]: row[1]
        for row in bind.execute(sa.text("SELECT codigo, id FROM saas_modulos")).fetchall()
    }
    plan_ids = {
        row[0]: row[1]
        for row in bind.execute(sa.text("SELECT codigo, id FROM saas_planos")).fetchall()
    }

    for codigo, _n, _d, _o, _p, _u, mods in _PLANOS:
        pid = plan_ids.get(codigo)
        if pid is None:
            continue
        bind.execute(
            sa.text("DELETE FROM saas_plano_modulos WHERE plano_id = :pid"),
            {"pid": pid},
        )
        for mc in mods:
            mid = mod_ids.get(mc)
            if mid is None:
                continue
            bind.execute(
                sa.text(
                    """
                    INSERT INTO saas_plano_modulos (plano_id, modulo_id)
                    VALUES (:pid, :mid)
                    ON CONFLICT DO NOTHING
                    """
                ),
                {"pid": pid, "mid": mid},
            )


def downgrade() -> None:
    """Não remove módulos/planos — catálogo comercial pode ter sido editado em produção."""
    pass
