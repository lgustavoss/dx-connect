"""
Cenário de demonstração com volume: redes, empresas, atendentes e tickets.

Execute a partir da pasta backend:
  python -m app.seed_demo_volume
  python -m app.seed_demo_volume --force

Pressupõe banco já migrado / create_all. Garante status de ticket e admin (via run_seed).

Atendentes criados (todos com senha **demo123**).
E-mails usam dominio exemplo.org (valido para o validador Pydantic; nao sao caixas reais):
  - suporte.demo1@exemplo.org
  - suporte.demo2@exemplo.org
  - financeiro.demo@exemplo.org
  - multi.demo@exemplo.org (Suporte + Financeiro)

Redes criadas têm prefixo "[Demo]" no nome para idempotência (sem --force não duplica).
"""

from __future__ import annotations

import argparse
import random
from datetime import datetime, timezone

from sqlalchemy import func

import bcrypt

from app.database import SessionLocal
from app.seed import run_seed
from app.services.protocolo_mensal import gerar_protocolo_ticket
from app.models import (
    Rede,
    Empresa,
    Setor,
    Atendente,
    StatusTicket,
    Ticket,
    TicketMensagem,
    TicketHistorico,
)

DEMO_REDE_PREFIX = "[Demo]"


def _hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _city_abbrev(cidade: str) -> str:
    return "".join(w[0] for w in cidade.split() if w)[:4].upper()


def _ensure_setores(db) -> dict[str, Setor]:
    specs = [
        ("Suporte", "suporte"),
        ("Financeiro", "financeiro"),
        ("Comercial", "comercial"),
    ]
    out: dict[str, Setor] = {}
    for nome, slug in specs:
        s = db.query(Setor).filter(Setor.slug == slug).first()
        if not s:
            s = Setor(nome=nome, slug=slug, ativo=True)
            db.add(s)
            db.commit()
            db.refresh(s)
            print(f"Setor criado: {nome}")
        out[slug] = s
    return out


def _status_por_slug(db) -> dict[str, StatusTicket]:
    rows = db.query(StatusTicket).filter(StatusTicket.ativo.is_(True)).all()
    by_slug: dict[str, StatusTicket] = {}
    for r in rows:
        if r.slug:
            by_slug[r.slug.lower()] = r
    needed = ["aguardando_atendimento", "em_atendimento", "aguardando_cliente", "resolvido", "fechado"]
    missing = [s for s in needed if s not in by_slug]
    if missing:
        raise SystemExit(
            f"Faltam status de ticket no banco: {missing}. Rode o app uma vez ou python -m app.seed"
        )
    return by_slug


def run_demo_volume(force: bool = False) -> None:
    run_seed()
    db = SessionLocal()
    try:
        if not force and db.query(Rede).filter(Rede.nome.like(f"{DEMO_REDE_PREFIX}%")).first():
            print("Dados demo já existem (redes com prefixo [Demo]). Use --force para recriar.")
            return

        setores = _ensure_setores(db)
        st = _status_por_slug(db)

        admin = db.query(Atendente).filter(func.lower(Atendente.email) == "admin@email.com").first()
        if not admin:
            raise SystemExit("Admin admin@email.com não encontrado. Rode python -m app.seed primeiro.")

        # Remove demo anterior ao --force
        if force:
            redes_demo = db.query(Rede).filter(Rede.nome.like(f"{DEMO_REDE_PREFIX}%")).all()
            for r in redes_demo:
                empresas = db.query(Empresa).filter(Empresa.rede_id == r.id).all()
                for emp in empresas:
                    tickets = db.query(Ticket).filter(Ticket.empresa_id == emp.id).all()
                    for t in tickets:
                        db.query(TicketMensagem).filter(TicketMensagem.ticket_id == t.id).delete(
                            synchronize_session=False
                        )
                        db.query(TicketHistorico).filter(TicketHistorico.ticket_id == t.id).delete(
                            synchronize_session=False
                        )
                        db.delete(t)
                    db.delete(emp)
                db.delete(r)
            for email in (
                "suporte.demo1@exemplo.org",
                "suporte.demo2@exemplo.org",
                "financeiro.demo@exemplo.org",
                "multi.demo@exemplo.org",
            ):
                a = db.query(Atendente).filter(func.lower(Atendente.email) == email.lower()).first()
                if a:
                    db.delete(a)
            db.commit()
            print("Base demo anterior removida.")

        nomes_redes = [
            "Grupo Horizonte",
            "Rede Atlântico",
            "Consórcio Sul",
            "Parceiros Centro",
            "Aliança Nordeste",
            "Vertex Brasil",
            "Nexus Comércio",
            "Prime Redes",
        ]

        redes: list[Rede] = []
        for nome in nomes_redes:
            r = Rede(nome=f"{DEMO_REDE_PREFIX} {nome}", ativo=True)
            db.add(r)
            redes.append(r)
        db.commit()
        for r in redes:
            db.refresh(r)

        empresas_por_rede: list[list[Empresa]] = []
        segmentos = ["Ltda", "S.A.", "ME", "EPP"]
        cidades = ["São Paulo", "Curitiba", "Belo Horizonte", "Porto Alegre", "Salvador", "Brasília"]

        for idx, r in enumerate(redes):
            empresas_r: list[Empresa] = []
            n_emp = 3 if idx % 2 == 0 else 4
            for j in range(n_emp):
                cidade = cidades[(idx + j) % len(cidades)]
                emp = Empresa(
                    rede_id=r.id,
                    nome=f"Empresa {_city_abbrev(cidade)} {idx + 1}-{j + 1} {segmentos[j % len(segmentos)]}",
                    cnpj_cpf=f"{str(10 + idx).zfill(2)}{str(j).zfill(3)}0001{str(10 + j).zfill(2)}",
                    cidade=cidade,
                    estado=["SP", "PR", "MG", "RS", "BA", "DF"][(idx + j) % 6],
                    ativo=True,
                )
                db.add(emp)
                empresas_r.append(emp)
            db.commit()
            for e in empresas_r:
                db.refresh(e)
            empresas_por_rede.append(empresas_r)

        # Atendentes
        specs_att: list[tuple[str, str, str, list[str]]] = [
            ("suporte.demo1@exemplo.org", "Ana Suporte", "atendente", ["suporte"]),
            ("suporte.demo2@exemplo.org", "Bruno Suporte", "atendente", ["suporte"]),
            ("financeiro.demo@exemplo.org", "Carla Financeiro", "atendente", ["financeiro"]),
            ("multi.demo@exemplo.org", "Diana Multi", "atendente", ["suporte", "financeiro"]),
        ]

        atendentes_criados: list[Atendente] = []
        for email, nome, role, slugs in specs_att:
            a = Atendente(
                email=email,
                nome=nome,
                senha_hash=_hash_senha("demo123"),
                role=role,
                ativo=True,
            )
            for sl in slugs:
                a.setores.append(setores[sl])
            db.add(a)
            atendentes_criados.append(a)
        db.commit()
        for a in atendentes_criados:
            db.refresh(a)

        suporte_atendentes = [a for a in atendentes_criados if a.email.startswith("suporte.demo")]
        financeiro_atendentes = [a for a in atendentes_criados if a.email.startswith("financeiro.demo")]
        multi = next(a for a in atendentes_criados if a.email.startswith("multi."))

        assuntos_pool = [
            "Faturamento não processado",
            "Erro ao acessar sistema",
            "Dúvida sobre NFS-e",
            "Solicitação de novo usuário",
            "Integração com banco",
            "Backup e restauração",
            "Treinamento equipe",
            "Ajuste cadastro empresa",
            "Relatório mensal",
            "Timeout na importação",
            "Liberação de módulo",
            "Cópia de segurança",
        ]

        descricoes_pool = [
            "Cliente relata urgência; precisamos validar logs.",
            "Ambiente de homologação ok; seguir em produção.",
            "Solicito análise da equipe técnica.",
            "Documentação anexa na próxima mensagem.",
            "Prioridade média — aguardando retorno do cliente.",
        ]

        # Distribui tickets: ~55
        random.seed(42)
        todos_status = [
            st["aguardando_atendimento"],
            st["em_atendimento"],
            st["aguardando_cliente"],
            st["resolvido"],
            st["fechado"],
        ]
        setor_rot = [setores["suporte"], setores["financeiro"], setores["comercial"]]

        flat_empresas: list[Empresa] = [e for row in empresas_por_rede for e in row]
        n_tickets = min(58, len(flat_empresas) * 8)

        for i in range(n_tickets):
            emp = flat_empresas[i % len(flat_empresas)]
            setor = setor_rot[i % 3]
            status = random.choice(todos_status)
            atend: Atendente | None = None
            if status.slug in ("em_atendimento", "aguardando_cliente", "resolvido"):
                if setor.slug == "financeiro" and financeiro_atendentes:
                    atend = financeiro_atendentes[0]
                elif setor.slug == "suporte" and suporte_atendentes:
                    atend = random.choice(suporte_atendentes)
                else:
                    atend = multi
            elif status.slug == "fechado":
                atend = random.choice(atendentes_criados)

            fechado_em = None
            if status.slug == "fechado":
                fechado_em = datetime.now(timezone.utc)

            protocolo = gerar_protocolo_ticket(db)
            ticket = Ticket(
                protocolo=protocolo,
                empresa_id=emp.id,
                setor_id=setor.id,
                status_id=status.id,
                atendente_id=atend.id if atend else None,
                assunto=f"{random.choice(assuntos_pool)} ({i + 1})",
                descricao=random.choice(descricoes_pool),
                fechado_em=fechado_em,
            )
            db.add(ticket)
            db.commit()
            db.refresh(ticket)

            db.add(
                TicketMensagem(
                    ticket_id=ticket.id,
                    atendente_id=admin.id,
                    tipo="abertura",
                    corpo=(ticket.descricao or "Abertura do chamado de demonstração.").strip(),
                )
            )

            if atend and random.random() < 0.35 and status.slug != "fechado":
                db.add(
                    TicketMensagem(
                        ticket_id=ticket.id,
                        atendente_id=atend.id,
                        tipo="publico",
                        corpo="Em análise pela equipe. Atualizo em breve.",
                    )
                )

            db.commit()

        print()
        print("=== Demo de volume criada ===")
        print(f"Redes: {len(redes)} | Empresas: {len(flat_empresas)} | Tickets: {n_tickets}")
        print("Atendentes (senha demo123):")
        for email, _, _, _ in specs_att:
            print(f"  - {email}")
        print()
    finally:
        db.close()


def main():
    p = argparse.ArgumentParser(description="Seed de volume para simulação (demo).")
    p.add_argument("--force", action="store_true", help="Remove demo anterior e recria")
    args = p.parse_args()
    run_demo_volume(force=args.force)


if __name__ == "__main__":
    main()
