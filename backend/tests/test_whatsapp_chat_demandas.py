"""Demandas por sessão de chat WhatsApp (#423)."""

from __future__ import annotations

from tests.test_whatsapp_chats import _webhook_body


def _seed_natureza_motivo(db_session):
    from app.models.ticket_classificacao import TicketMotivo, TicketNatureza

    nat = TicketNatureza(nome="Dúvida WPP", slug="duvida-wpp-test", ordem=1, ativo=True)
    db_session.add(nat)
    db_session.flush()
    mot = TicketMotivo(natureza_id=nat.id, nome="Operacional WPP", slug="oper-wpp-test", ordem=1, ativo=True)
    db_session.add(mot)
    db_session.commit()
    return nat, mot


def _chat_em_atendimento(client, auth_headers, *, wa_id="5511999001122", msg_id="dm-base"):
    client.patch(
        "/v1/settings/whatsapp",
        json={"webhook_secret": "demandas-test"},
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": "demandas-test"}
    client.post("/v1/webhooks/evolution", json=_webhook_body(wa_id=wa_id, msg_id=msg_id), headers=h)
    cid = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"]).json()[0]["id"]
    client.post(f"/v1/whatsapp/chats/{cid}/assumir", headers=auth_headers["a1"])
    return cid


def test_registrar_e_listar_demanda(client, seed_base, auth_headers, db_session):
    nat, mot = _seed_natureza_motivo(db_session)
    cid = _chat_em_atendimento(client, auth_headers, msg_id="dm-1")

    r = client.post(
        f"/v1/whatsapp/chats/{cid}/demandas",
        json={"natureza_id": nat.id, "motivo_id": mot.id, "descricao_curta": "Cliente pediu 2ª via"},
        headers=auth_headers["a1"],
    )
    assert r.status_code == 201
    body = r.json()
    assert body["desfecho"] == "resolvido_sessao"
    assert body["natureza_nome"] == "Dúvida WPP"
    assert body["motivo_nome"] == "Operacional WPP"

    listed = client.get(f"/v1/whatsapp/chats/{cid}/demandas", headers=auth_headers["a1"]).json()
    assert len(listed) == 1
    assert listed[0]["id"] == body["id"]


def test_abrir_ticket_cria_demanda_escalada(client, seed_base, auth_headers, db_session):
    nat, mot = _seed_natureza_motivo(db_session)
    cid = _chat_em_atendimento(client, auth_headers, wa_id="5511999002233", msg_id="dm-2")

    r = client.post(
        f"/v1/whatsapp/chats/{cid}/abrir-ticket",
        json={
            "empresa_id": seed_base["empresa"].id,
            "setor_id": seed_base["setor1"].id,
            "assunto": "Escalado via chat",
            "descricao": "Detalhe",
            "natureza_id": nat.id,
            "motivo_id": mot.id,
        },
        headers=auth_headers["a1"],
    )
    assert r.status_code == 200
    ticket_ids = r.json()["ticket_ids"]
    assert ticket_ids

    demandas = client.get(f"/v1/whatsapp/chats/{cid}/demandas", headers=auth_headers["a1"]).json()
    assert len(demandas) == 1
    assert demandas[0]["desfecho"] == "escalado_ticket"
    assert demandas[0]["ticket_id"] == ticket_ids[-1]


def test_outro_atendente_nao_registra_demanda(client, seed_base, auth_headers, db_session):
    nat, _ = _seed_natureza_motivo(db_session)
    cid = _chat_em_atendimento(client, auth_headers, wa_id="5511999003344", msg_id="dm-3")

    denied = client.post(
        f"/v1/whatsapp/chats/{cid}/demandas",
        json={"natureza_id": nat.id},
        headers=auth_headers["a2"],
    )
    assert denied.status_code == 403


def test_dashboard_agrega_demandas_por_natureza(client, seed_base, auth_headers, db_session):
    nat, mot = _seed_natureza_motivo(db_session)
    cid = _chat_em_atendimento(client, auth_headers, wa_id="5511999004455", msg_id="dm-4")
    client.post(
        f"/v1/whatsapp/chats/{cid}/demandas",
        json={"natureza_id": nat.id, "motivo_id": mot.id},
        headers=auth_headers["a1"],
    )

    dash = client.get("/v1/dashboard/chats", headers=auth_headers["admin"]).json()
    row = next((x for x in dash["demandas_por_natureza"] if x["id"] == nat.id), None)
    assert row is not None
    assert row["total"] >= 1
    assert row["nome"] == "Dúvida WPP"
