"""Testes do relatório de chats WhatsApp (#285 / D-F4)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.whatsapp_chat import WhatsappChat


def _criar_chat(db_session, seed_base):
    agora = datetime.now(timezone.utc)
    suf = datetime.now().timestamp()
    c = WhatsappChat(
        protocolo=f"RC{suf}",
        wa_id=f"5511888{suf}",
        cliente_nome="Cliente relatório",
        estado="encerrado",
        setor_id=seed_base["setor1"].id,
        atendente_id=seed_base["admin"].id,
        created_at=agora - timedelta(hours=2),
        atendimento_inicio_at=agora - timedelta(hours=1),
        encerramento_at=agora,
        avaliacao_nota=5,
        avaliacao_respondida_at=agora,
    )
    db_session.add(c)
    db_session.commit()
    return c


def test_relatorio_chats_admin_json(client, seed_base, auth_headers, db_session):
    _criar_chat(db_session, seed_base)
    r = client.get("/v1/relatorios/chats", headers=auth_headers["admin"])
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert len(body["itens"]) >= 1
    assert body["itens"][0]["protocolo"]
    assert body["itens"][0]["cliente_nome"] == "Cliente relatório"


def test_relatorio_chats_atendente_403(client, seed_base, auth_headers, db_session):
    _criar_chat(db_session, seed_base)
    r = client.get("/v1/relatorios/chats", headers=auth_headers["a1"])
    assert r.status_code == 403


def test_relatorio_chats_export_csv(client, seed_base, auth_headers, db_session):
    _criar_chat(db_session, seed_base)
    r = client.get(
        "/v1/relatorios/chats",
        headers=auth_headers["admin"],
        params={"format": "csv"},
    )
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    text = r.text
    assert text.startswith("\ufeff")
    assert "protocolo" in text
    assert "Cliente relatório" in text
