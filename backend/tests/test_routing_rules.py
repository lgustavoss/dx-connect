"""Testes do motor de roteamento (#258)."""

from __future__ import annotations

from app.core.routing import RoutingCanal
from app.models import AuditLog, Ticket, TicketHistorico
from app.models.routing_rule import RoutingRule
from app.models.ticket_classificacao import TicketMotivo, TicketNatureza
from app.services.routing_apply import CAMPO_HISTORICO_ROTEAMENTO, resolver_motivo_roteamento
from app.services.routing_evaluate import RoutingContext, evaluate_routing


def _criar_regra(db, seed_base, *, nome, condicoes, acoes, ordem=0, rede_id=None, ativo=True):
    rule = RoutingRule(
        tenant_id=1,
        nome=nome,
        ativo=ativo,
        ordem=ordem,
        rede_id=rede_id,
        condicoes=condicoes,
        acoes=acoes,
    )
    db.add(rule)
    db.flush()
    return rule


def _seed_natureza_motivo(db_session):
    nat = TicketNatureza(nome="Financeiro", slug="fin_test", ordem=1, ativo=True)
    db_session.add(nat)
    db_session.flush()
    mot = TicketMotivo(natureza_id=nat.id, nome="Boleto", slug="boleto_test", ordem=1, ativo=True)
    db_session.add(mot)
    db_session.flush()
    return nat, mot


def test_evaluate_contains_assunto(db_session, seed_base):
    _criar_regra(
        db_session,
        seed_base,
        nome="NF financeiro",
        condicoes=[{"campo": "assunto", "operador": "contains", "valor": "NF"}],
        acoes={"setor_id": seed_base["setor2"].id, "prioridade": "alta"},
    )
    db_session.commit()

    ctx = RoutingContext(assunto="Entrada de NF cliente X", canal=RoutingCanal.email)
    r = evaluate_routing(db_session, tenant_id=1, context=ctx)
    assert r.matched is True
    assert r.setor_id == seed_base["setor2"].id
    assert r.prioridade.value == "alta"


def test_evaluate_regex_assunto(db_session, seed_base):
    _criar_regra(
        db_session,
        seed_base,
        nome="Protocolo numerico",
        condicoes=[{"campo": "assunto", "operador": "regex", "valor": r"NF-\d{4}"}],
        acoes={"setor_id": seed_base["setor2"].id},
    )
    db_session.commit()

    ctx = RoutingContext(assunto="Entrada NF-2024 cliente", canal=RoutingCanal.email)
    r = evaluate_routing(db_session, tenant_id=1, context=ctx)
    assert r.matched is True
    assert r.setor_id == seed_base["setor2"].id

    ctx_fail = RoutingContext(assunto="Entrada NF cliente", canal=RoutingCanal.email)
    assert evaluate_routing(db_session, tenant_id=1, context=ctx_fail).matched is False


def test_evaluate_email_from_domain(db_session, seed_base):
    _criar_regra(
        db_session,
        seed_base,
        nome="Financeiro remetente",
        condicoes=[{"campo": "email_from", "operador": "contains", "valor": "@financeiro."}],
        acoes={"setor_id": seed_base["setor2"].id},
        ordem=0,
    )
    db_session.commit()

    ctx = RoutingContext(email_from="contato@financeiro.empresa.com", canal=RoutingCanal.email)
    r = evaluate_routing(db_session, tenant_id=1, context=ctx)
    assert r.matched is True
    assert r.setor_id == seed_base["setor2"].id


def test_primeira_regra_ganha(db_session, seed_base):
    _criar_regra(
        db_session,
        seed_base,
        nome="Geral",
        ordem=0,
        condicoes=[{"campo": "canal", "operador": "equals", "valor": "email"}],
        acoes={"setor_id": seed_base["setor1"].id},
    )
    _criar_regra(
        db_session,
        seed_base,
        nome="NF",
        ordem=1,
        condicoes=[{"campo": "assunto", "operador": "contains", "valor": "NF"}],
        acoes={"setor_id": seed_base["setor2"].id},
    )
    db_session.commit()

    ctx = RoutingContext(assunto="NF entrada", canal=RoutingCanal.email)
    r = evaluate_routing(db_session, tenant_id=1, context=ctx)
    assert r.rule_nome == "Geral"
    assert r.setor_id == seed_base["setor1"].id


def test_escopo_rede(db_session, seed_base):
    _criar_regra(
        db_session,
        seed_base,
        nome="Só rede",
        rede_id=seed_base["rede"].id,
        condicoes=[{"campo": "assunto", "operador": "contains", "valor": "PDV"}],
        acoes={"setor_id": seed_base["setor2"].id},
    )
    db_session.commit()

    ctx_ok = RoutingContext(assunto="PDV offline", rede_id=seed_base["rede"].id, canal=RoutingCanal.manual)
    assert evaluate_routing(db_session, tenant_id=1, context=ctx_ok).matched is True

    ctx_fail = RoutingContext(assunto="PDV offline", rede_id=999, canal=RoutingCanal.manual)
    assert evaluate_routing(db_session, tenant_id=1, context=ctx_fail).matched is False


def test_resolver_motivo_por_natureza(db_session):
    nat, mot = _seed_natureza_motivo(db_session)
    db_session.commit()
    mid = resolver_motivo_roteamento(db_session, natureza_id=nat.id, motivo_id=None)
    assert mid == mot.id


def test_crud_routing_rules(client, seed_base, auth_headers, db_session):
    r = client.post(
        "/v1/routing/rules",
        headers=auth_headers["admin"],
        json={
            "nome": "Regra teste",
            "ativo": True,
            "rede_id": None,
            "condicoes": [{"campo": "assunto", "operador": "equals", "valor": "Urgente"}],
            "acoes": {"setor_id": seed_base["setor1"].id},
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    rule_id = body["id"]
    assert body["nome"] == "Regra teste"

    r2 = client.get("/v1/routing/rules", headers=auth_headers["admin"])
    assert r2.status_code == 200
    assert len(r2.json()) >= 1

    r3 = client.post(
        "/v1/routing/rules/simulate",
        headers=auth_headers["admin"],
        json={"assunto": "Urgente", "canal": "manual"},
    )
    assert r3.status_code == 200
    sim = r3.json()
    assert sim["matched"] is True
    assert sim["setor_id"] == seed_base["setor1"].id

    r4 = client.delete(f"/v1/routing/rules/{rule_id}", headers=auth_headers["admin"])
    assert r4.status_code == 204


def test_routing_rules_admin_only(client, seed_base, auth_headers):
    r = client.get("/v1/routing/rules", headers=auth_headers["a1"])
    assert r.status_code == 403


def test_criar_ticket_com_roteamento(client, seed_base, auth_headers, db_session):
    _criar_regra(
        db_session,
        seed_base,
        nome="Assunto financeiro",
        condicoes=[{"campo": "assunto", "operador": "contains", "valor": "boleto"}],
        acoes={"setor_id": seed_base["setor2"].id},
    )
    db_session.commit()

    r = client.post(
        "/v1/tickets",
        headers=auth_headers["admin"],
        json={
            "empresa_id": seed_base["empresa"].id,
            "assunto": "Cobrança boleto vencido",
            "descricao": "Teste roteamento",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["setor_id"] == seed_base["setor2"].id

    hist = (
        db_session.query(TicketHistorico)
        .filter(TicketHistorico.ticket_id == body["id"], TicketHistorico.campo == CAMPO_HISTORICO_ROTEAMENTO)
        .first()
    )
    assert hist is not None
    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_type == "routing_rule", AuditLog.action == "apply")
        .first()
    )
    assert audit is not None


def test_criar_ticket_setor_explicito_nao_sobrescrito(client, seed_base, auth_headers, db_session):
    _criar_regra(
        db_session,
        seed_base,
        nome="Boleto financeiro",
        condicoes=[{"campo": "assunto", "operador": "contains", "valor": "boleto"}],
        acoes={"setor_id": seed_base["setor2"].id},
    )
    db_session.commit()

    r = client.post(
        "/v1/tickets",
        headers=auth_headers["admin"],
        json={
            "empresa_id": seed_base["empresa"].id,
            "setor_id": seed_base["setor1"].id,
            "assunto": "Cobrança boleto",
            "descricao": "Setor explícito",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["setor_id"] == seed_base["setor1"].id


def test_aplicar_roteamento_so_admin(client, seed_base, auth_headers, db_session):
    _criar_regra(
        db_session,
        seed_base,
        nome="Força financeiro",
        condicoes=[{"campo": "assunto", "operador": "contains", "valor": "boleto"}],
        acoes={"setor_id": seed_base["setor2"].id},
    )
    db_session.commit()

    r = client.post(
        "/v1/tickets",
        headers=auth_headers["a1"],
        json={
            "empresa_id": seed_base["empresa"].id,
            "setor_id": seed_base["setor1"].id,
            "assunto": "boleto",
            "descricao": "x",
            "aplicar_roteamento": True,
        },
    )
    assert r.status_code == 403


def test_aplicar_roteamento_admin_sobrescreve_setor(client, seed_base, auth_headers, db_session):
    _criar_regra(
        db_session,
        seed_base,
        nome="Força financeiro admin",
        condicoes=[{"campo": "assunto", "operador": "contains", "valor": "boleto"}],
        acoes={"setor_id": seed_base["setor2"].id},
    )
    db_session.commit()

    r = client.post(
        "/v1/tickets",
        headers=auth_headers["admin"],
        json={
            "empresa_id": seed_base["empresa"].id,
            "setor_id": seed_base["setor1"].id,
            "assunto": "boleto",
            "descricao": "x",
            "aplicar_roteamento": True,
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["setor_id"] == seed_base["setor2"].id


def test_roteamento_atribui_atendente(client, seed_base, auth_headers, db_session):
    _criar_regra(
        db_session,
        seed_base,
        nome="Atribui a1",
        condicoes=[{"campo": "assunto", "operador": "equals", "valor": "VIP"}],
        acoes={"setor_id": seed_base["setor1"].id, "atendente_id": seed_base["a1"].id},
    )
    db_session.commit()

    r = client.post(
        "/v1/tickets",
        headers=auth_headers["admin"],
        json={
            "empresa_id": seed_base["empresa"].id,
            "assunto": "VIP",
            "descricao": "x",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["atendente_id"] == seed_base["a1"].id


def test_roteamento_natureza_define_motivo(client, seed_base, auth_headers, db_session):
    nat, mot = _seed_natureza_motivo(db_session)
    _criar_regra(
        db_session,
        seed_base,
        nome="Classif financeiro",
        condicoes=[{"campo": "assunto", "operador": "contains", "valor": "cobrança"}],
        acoes={"setor_id": seed_base["setor1"].id, "natureza_id": nat.id},
    )
    db_session.commit()

    r = client.post(
        "/v1/tickets",
        headers=auth_headers["admin"],
        json={
            "empresa_id": seed_base["empresa"].id,
            "assunto": "cobrança mensal",
            "descricao": "x",
        },
    )
    assert r.status_code == 201, r.text
    t = db_session.query(Ticket).filter(Ticket.id == r.json()["id"]).first()
    assert t.motivo_id == mot.id


def _minimal_rfc822_nf(message_id: str = "<routing-nf@dx.test>") -> str:
    return (
        f"From: Cliente <cliente@example.com>\r\n"
        f"To: suporte@dxconnect.local\r\n"
        f"Subject: Entrada NF cliente\r\n"
        f"Message-ID: {message_id}\r\n"
        f"MIME-Version: 1.0\r\n"
        f"Content-Type: text/plain; charset=utf-8\r\n"
        f"\r\n"
        f"Corpo NF.\r\n"
    )


def test_webhook_inbound_aplica_regra_roteamento(client, seed_base, monkeypatch, db_session):
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_WEBHOOK_SECRET", "segredo-routing")
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_EMPRESA_ID", seed_base["empresa"].id)
    monkeypatch.setattr("app.config.settings.EMAIL_INBOUND_DEFAULT_SETOR_ID", seed_base["setor1"].id)

    _criar_regra(
        db_session,
        seed_base,
        nome="NF para financeiro",
        condicoes=[{"campo": "assunto", "operador": "contains", "valor": "NF"}],
        acoes={"setor_id": seed_base["setor2"].id},
    )
    db_session.commit()

    mid = "<inbound-routing-nf@dx.test>"
    r = client.post(
        "/v1/webhooks/email-inbound",
        headers={"X-Dx-Email-Webhook-Secret": "segredo-routing"},
        json={"rfc822": _minimal_rfc822_nf(mid)},
    )
    assert r.status_code == 200, r.text
    ticket_id = r.json()["ticket_id"]
    t = db_session.query(Ticket).filter(Ticket.id == ticket_id).first()
    assert t.setor_id == seed_base["setor2"].id

    hist = (
        db_session.query(TicketHistorico)
        .filter(TicketHistorico.ticket_id == ticket_id, TicketHistorico.campo == CAMPO_HISTORICO_ROTEAMENTO)
        .first()
    )
    assert hist is not None
