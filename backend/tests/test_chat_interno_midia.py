"""Testes de mídia no chat interno (#495)."""

from __future__ import annotations

from app.services import chat_interno as chat_svc


def _criar_direta(client, headers, atendente_id: int) -> dict:
    r = client.post(
        "/v1/chat-interno/conversas/direta",
        json={"atendente_id": atendente_id},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _png_bytes() -> bytes:
    # PNG mínimo 1x1 (válido para upload)
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x01\x01\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def test_upload_imagem_conversa_direta(client, seed_base, auth_headers):
    conv = _criar_direta(client, auth_headers["a1"], seed_base["admin"].id)
    png = _png_bytes()

    r = client.post(
        f"/v1/chat-interno/conversas/{conv['id']}/mensagens/midia",
        data={"mediatipo": "imagem", "caption": "Print do sistema"},
        files={"file": ("captura.png", png, "image/png")},
        headers=auth_headers["a1"],
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["tipo_midia"] == "imagem"
    assert body["midia_disponivel"] is True
    assert body["corpo"] == "Print do sistema"
    assert body["nome_arquivo"] == "captura.png"

    r_inbox = client.get("/v1/chat-interno/conversas", headers=auth_headers["admin"])
    assert r_inbox.json()[0]["ultima_mensagem_corpo"] == "Print do sistema"


def test_download_midia_rbac(client, seed_base, auth_headers):
    conv = _criar_direta(client, auth_headers["a1"], seed_base["a2"].id)
    png = _png_bytes()
    up = client.post(
        f"/v1/chat-interno/conversas/{conv['id']}/mensagens/midia",
        data={"mediatipo": "imagem", "caption": ""},
        files={"file": ("foto.png", png, "image/png")},
        headers=auth_headers["a1"],
    )
    msg_id = up.json()["id"]

    dl_ok = client.get(
        f"/v1/chat-interno/conversas/{conv['id']}/mensagens/{msg_id}/download",
        headers=auth_headers["a2"],
    )
    assert dl_ok.status_code == 200
    assert dl_ok.content == png

    dl_forbidden = client.get(
        f"/v1/chat-interno/conversas/{conv['id']}/mensagens/{msg_id}/download",
        headers=auth_headers["admin"],
    )
    assert dl_forbidden.status_code == 403


def test_upload_documento_canal_setor(client, seed_base, auth_headers):
    setor1 = seed_base["setor1"].id
    canal = client.get(f"/v1/chat-interno/setores/{setor1}/canal", headers=auth_headers["a1"]).json()

    r = client.post(
        f"/v1/chat-interno/setores/{setor1}/canal/mensagens/midia",
        data={"mediatipo": "documento", "caption": ""},
        files={"file": ("aviso.txt", b"Comunicado em anexo", "text/plain")},
        headers=auth_headers["a1"],
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["tipo_midia"] == "documento"
    assert body["conversa_id"] == canal["id"]
    assert "📄" in body["corpo"] or body["corpo"] == "📄 Documento"


def test_tipo_midia_invalido(client, seed_base, auth_headers):
    conv = _criar_direta(client, auth_headers["a1"], seed_base["admin"].id)
    r = client.post(
        f"/v1/chat-interno/conversas/{conv['id']}/mensagens/midia",
        data={"mediatipo": "figurinha", "caption": ""},
        files={"file": ("x.bin", b"123", "application/octet-stream")},
        headers=auth_headers["a1"],
    )
    assert r.status_code == 400


def test_emit_midia_inclui_tipo(client, seed_base, db_session, monkeypatch):
    a1 = seed_base["a1"]
    admin = seed_base["admin"]
    conversa = chat_svc.obter_ou_criar_conversa_direta(db_session, 1, a1.id, admin.id)
    mensagem = chat_svc.enviar_mensagem_midia(
        db_session,
        conversa,
        a1,
        tipo_midia="imagem",
        data=_png_bytes(),
        mimetype="image/png",
        nome_original="f.png",
        caption="",
    )
    db_session.commit()

    eventos: list[dict] = []

    def fake_publish(atendente_ids, event_type, payload):
        if event_type == "chat.interno.mensagem":
            eventos.append(payload)

    monkeypatch.setattr("app.services.realtime_emit._publish_to_atendentes", fake_publish)
    monkeypatch.setattr("app.services.realtime_emit._emit_notificacao_after_counter_change", lambda db: None)

    from app.services.realtime_emit import emit_chat_interno_mensagem

    emit_chat_interno_mensagem(db_session, conversa, mensagem, exclude_atendente_id=a1.id)

    assert len(eventos) == 1
    assert eventos[0]["tipo_midia"] == "imagem"
    assert "Imagem" in eventos[0]["corpo_preview"]
