"""#1012 — chats e tickets por contato (funcionario_rede_id)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models import Ticket
from app.models.funcionario_rede import FuncionarioRede
from app.models.whatsapp_chat import WhatsappChat, WhatsappChatTicket


def _criar_funcionario(db_session, seed_base, *, email="contato@example.com"):
    f = FuncionarioRede(
        nome="Contato Teste",
        email=email,
        telefone="5511999887766",
        tipo="colaborador",
        escopo_empresas="selected",
        ativo=True,
        rede_id=seed_base["rede"].id,
        empresa_id=seed_base["empresa"].id,
    )
    db_session.add(f)
    db_session.flush()
    return f


def _protocolo(prefix: str) -> str:
    return f"{prefix}{datetime.now(timezone.utc).timestamp()}"


def test_atendente_obtem_funcionario_rede(client, seed_base, auth_headers, db_session):
    f = _criar_funcionario(db_session, seed_base)
    db_session.commit()

    r = client.get(f"/v1/funcionarios-rede/{f.id}", headers=auth_headers["a1"])
    assert r.status_code == 200
    body = r.json()
    assert body["telefone"] == "5511999887766"
    assert body["rede_nome"] == seed_base["rede"].nome
    assert len(body["empresas_vinculo"]) == 1
    assert body["empresas_vinculo"][0]["id"] == seed_base["empresa"].id


def test_atendente_403_lista_funcionarios_rede_inalterado(client, auth_headers):
    r = client.get("/v1/funcionarios-rede", headers=auth_headers["a1"])
    assert r.status_code == 403


def test_tickets_por_funcionario_rede_uniao(client, seed_base, auth_headers, db_session):
    f = _criar_funcionario(db_session, seed_base, email="uniao@example.com")
    t_portal = Ticket(
        tenant_id=1,
        protocolo=_protocolo("TP-"),
        empresa_id=seed_base["empresa"].id,
        setor_id=seed_base["setor1"].id,
        status_id=seed_base["status"].id,
        assunto="Portal",
        aberto_por_id=f.id,
    )
    t_chat = Ticket(
        tenant_id=1,
        protocolo=_protocolo("TC-"),
        empresa_id=seed_base["empresa"].id,
        setor_id=seed_base["setor1"].id,
        status_id=seed_base["status"].id,
        assunto="Via chat",
    )
    db_session.add_all([t_portal, t_chat])
    db_session.flush()
    chat = WhatsappChat(
        protocolo=_protocolo("WC-"),
        wa_id="5511888776655",
        estado="encerrado",
        setor_id=seed_base["setor1"].id,
        funcionario_rede_id=f.id,
        empresa_id=seed_base["empresa"].id,
        atendente_id=seed_base["a1"].id,
    )
    db_session.add(chat)
    db_session.flush()
    db_session.add(WhatsappChatTicket(chat_id=chat.id, ticket_id=t_chat.id, atendente_id=seed_base["a1"].id))
    db_session.commit()

    r = client.get(
        f"/v1/tickets?funcionario_rede_id={f.id}&situacao=todos",
        headers=auth_headers["a1"],
    )
    assert r.status_code == 200
    ids = {item["id"] for item in r.json()["items"]}
    assert t_portal.id in ids
    assert t_chat.id in ids
    assert len(ids) == 2


def test_tickets_funcionario_rede_inexistente_404(client, auth_headers):
    r = client.get("/v1/tickets?funcionario_rede_id=999999&situacao=abertos", headers=auth_headers["a1"])
    assert r.status_code == 404


def test_tickets_funcionario_rede_respeita_escopo_setor(client, seed_base, auth_headers, db_session):
    f = _criar_funcionario(db_session, seed_base, email="setor@example.com")
    t_setor1 = Ticket(
        tenant_id=1,
        protocolo=_protocolo("TS1-"),
        empresa_id=seed_base["empresa"].id,
        setor_id=seed_base["setor1"].id,
        status_id=seed_base["status"].id,
        assunto="Setor 1",
        aberto_por_id=f.id,
    )
    t_setor2 = Ticket(
        tenant_id=1,
        protocolo=_protocolo("TS2-"),
        empresa_id=seed_base["empresa"].id,
        setor_id=seed_base["setor2"].id,
        status_id=seed_base["status"].id,
        assunto="Setor 2",
        aberto_por_id=f.id,
    )
    db_session.add_all([t_setor1, t_setor2])
    db_session.commit()

    r_a1 = client.get(
        f"/v1/tickets?funcionario_rede_id={f.id}&situacao=todos",
        headers=auth_headers["a1"],
    )
    assert r_a1.status_code == 200
    ids_a1 = {item["id"] for item in r_a1.json()["items"]}
    assert t_setor1.id in ids_a1
    assert t_setor2.id not in ids_a1

    r_a2 = client.get(
        f"/v1/tickets?funcionario_rede_id={f.id}&situacao=todos",
        headers=auth_headers["a2"],
    )
    assert r_a2.status_code == 200
    ids_a2 = {item["id"] for item in r_a2.json()["items"]}
    assert t_setor2.id in ids_a2
    assert t_setor1.id not in ids_a2


def test_chats_encerrados_por_funcionario_rede(client, seed_base, auth_headers, db_session):
    f = _criar_funcionario(db_session, seed_base, email="chats@example.com")
    chat = WhatsappChat(
        protocolo=_protocolo("WA-"),
        wa_id="5511777666555",
        estado="em_atendimento",
        setor_id=seed_base["setor1"].id,
        funcionario_rede_id=f.id,
        atendente_id=seed_base["a1"].id,
        empresa_id=seed_base["empresa"].id,
    )
    db_session.add(chat)
    db_session.commit()

    r = client.get(
        f"/v1/whatsapp/chats/encerrados?funcionario_rede_id={f.id}&estado=todos",
        headers=auth_headers["a1"],
    )
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["id"] == chat.id


def test_chats_funcionario_rede_respeita_escopo_setor(client, seed_base, auth_headers, db_session):
    f = _criar_funcionario(db_session, seed_base, email="chatsetor@example.com")
    chat_s1 = WhatsappChat(
        protocolo=_protocolo("CS1-"),
        wa_id="5511666555444",
        estado="encerrado",
        setor_id=seed_base["setor1"].id,
        funcionario_rede_id=f.id,
        atendente_id=seed_base["a1"].id,
        empresa_id=seed_base["empresa"].id,
    )
    chat_s2 = WhatsappChat(
        protocolo=_protocolo("CS2-"),
        wa_id="5511555444333",
        estado="encerrado",
        setor_id=seed_base["setor2"].id,
        funcionario_rede_id=f.id,
        atendente_id=seed_base["a2"].id,
        empresa_id=seed_base["empresa"].id,
    )
    db_session.add_all([chat_s1, chat_s2])
    db_session.commit()

    r_a1 = client.get(
        f"/v1/whatsapp/chats/encerrados?funcionario_rede_id={f.id}&estado=todos",
        headers=auth_headers["a1"],
    )
    assert r_a1.status_code == 200
    ids_a1 = {item["id"] for item in r_a1.json()["items"]}
    assert chat_s1.id in ids_a1
    assert chat_s2.id not in ids_a1


def test_chats_funcionario_rede_inexistente_404(client, auth_headers):
    r = client.get(
        "/v1/whatsapp/chats/encerrados?funcionario_rede_id=999999&estado=todos",
        headers=auth_headers["a1"],
    )
    assert r.status_code == 404
