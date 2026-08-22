"""Geração de protocolos mensais #T / #C (#138)."""

from __future__ import annotations

from datetime import datetime

from app.services.protocolo_mensal import PROTOCOL_TZ, gerar_protocolo_chat, gerar_protocolo_solicitacao, gerar_protocolo_ticket


def test_protocolo_ticket_formato_e_sequencia(db_session, seed_base):
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        ref = datetime(2026, 1, 15, 12, 0, tzinfo=PROTOCOL_TZ)
        p1 = gerar_protocolo_ticket(db, ref=ref)
        p2 = gerar_protocolo_ticket(db, ref=ref)
        assert p1 == "#T202601-0001"
        assert p2 == "#T202601-0002"
        db.commit()
    finally:
        db.close()


def test_protocolo_chat_independente_do_ticket(db_session, seed_base):
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        ref = datetime(2026, 2, 20, 8, 0, tzinfo=PROTOCOL_TZ)
        c1 = gerar_protocolo_chat(db, ref=ref)
        t1 = gerar_protocolo_ticket(db, ref=ref)
        c2 = gerar_protocolo_chat(db, ref=ref)
        assert c1 == "#C202602-0001"
        assert t1 == "#T202602-0001"
        assert c2 == "#C202602-0002"
        db.commit()
    finally:
        db.close()


def test_protocolo_solicitacao_independente_de_ticket_e_chat(db_session, seed_base):
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        ref = datetime(2026, 8, 22, 16, 0, tzinfo=PROTOCOL_TZ)
        s1 = gerar_protocolo_solicitacao(db, ref=ref)
        t1 = gerar_protocolo_ticket(db, ref=ref)
        s2 = gerar_protocolo_solicitacao(db, ref=ref)
        assert s1 == "#S202608-0001"
        assert t1 == "#T202608-0001"
        assert s2 == "#S202608-0002"
        db.commit()
    finally:
        db.close()


def test_protocolo_troca_de_mes(db_session, seed_base):
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        p_abril = gerar_protocolo_ticket(db, ref=datetime(2026, 4, 30, 23, 0, tzinfo=PROTOCOL_TZ))
        p_maio = gerar_protocolo_ticket(db, ref=datetime(2026, 5, 1, 1, 0, tzinfo=PROTOCOL_TZ))
        assert "202604" in p_abril
        assert "202605" in p_maio
        assert p_maio.endswith("-0001")
        db.commit()
    finally:
        db.close()


def test_post_ticket_retorna_protocolo_novo(client, seed_base, auth_headers):
    t = client.post(
        "/v1/tickets",
        headers=auth_headers["admin"],
        json={
            "empresa_id": seed_base["empresa"].id,
            "setor_id": seed_base["setor1"].id,
            "assunto": "Proto",
            "descricao": "x",
        },
    )
    assert t.status_code == 201, t.text
    body = t.json()
    assert body["protocolo"].startswith("#T")
    assert body["protocolo"].count("-") == 1


def test_webhook_chat_protocolo_novo(client, seed_base, auth_headers):
    client.patch(
        "/v1/settings/whatsapp",
        json={"webhook_secret": "proto-test"},
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": "proto-test"}
    r = client.post(
        "/v1/webhooks/evolution",
        json={
            "event": "messages.upsert",
            "data": {
                "messages": [
                    {
                        "key": {
                            "remoteJid": "5511777889900@s.whatsapp.net",
                            "fromMe": False,
                            "id": "mid-proto-1",
                        },
                        "message": {"conversation": "Oi"},
                    }
                ]
            },
        },
        headers=h,
    )
    assert r.status_code == 200
    fila = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"]).json()
    assert len(fila) == 1
    assert fila[0]["protocolo"].startswith("#C")
