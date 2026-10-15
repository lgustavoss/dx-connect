"""Galeria pessoal de figurinhas do atendente (#S202610-0001)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.whatsapp_chat import WhatsappChat, WhatsappMensagem
from app.services import whatsapp_media_retencao as retencao
from app.services.whatsapp_media_storage import gravar_bytes_em_disco

WEBP_FAKE = b"RIFF\x24\x00\x00\x00WEBPVP8 figurinha-de-teste"


def _chat_com_figurinha(db_session, seed_base, tmp_path, monkeypatch, *, tipo="figurinha", wa_mid="wa-fig-1"):
    monkeypatch.setattr("app.config.settings.WHATSAPP_MEDIA_DIR", str(tmp_path))
    monkeypatch.setattr("app.services.whatsapp_media_storage.settings.WHATSAPP_MEDIA_DIR", str(tmp_path))
    nome = gravar_bytes_em_disco(WEBP_FAKE, "image/webp")
    assert nome
    chat = WhatsappChat(
        protocolo="FIG-0001",
        wa_id="5511999000777",
        cliente_nome="Cliente figurinha",
        estado="em_atendimento",
        setor_id=seed_base["setor1"].id,
        atendente_id=seed_base["a1"].id,
        atendimento_inicio_at=datetime.now(timezone.utc),
    )
    db_session.add(chat)
    db_session.flush()
    msg = WhatsappMensagem(
        chat_id=chat.id,
        direcao="inbound",
        corpo="[Figurinha]",
        tipo_midia=tipo,
        mimetype="image/webp",
        midia_nome_arquivo=nome,
        wa_message_id=wa_mid,
        midia_estado=retencao.MIDIA_ATIVA,
    )
    db_session.add(msg)
    db_session.commit()
    return chat, msg, nome


def test_salvar_listar_baixar_e_remover_figurinha(client, seed_base, auth_headers, db_session, tmp_path, monkeypatch):
    chat, msg, nome_msg = _chat_com_figurinha(db_session, seed_base, tmp_path, monkeypatch)
    h = auth_headers["a1"]

    r = client.post("/v1/whatsapp/figurinhas/de-mensagem", json={"chat_id": chat.id, "mensagem_id": msg.id}, headers=h)
    assert r.status_code == 200, r.text
    fig = r.json()
    assert fig["mimetype"] == "image/webp"

    again = client.post("/v1/whatsapp/figurinhas/de-mensagem", json={"chat_id": chat.id, "mensagem_id": msg.id}, headers=h)
    assert again.status_code == 200
    assert again.json()["id"] == fig["id"]

    lista = client.get("/v1/whatsapp/figurinhas", headers=h)
    assert [f["id"] for f in lista.json()] == [fig["id"]]

    arq = client.get(f"/v1/whatsapp/figurinhas/{fig['id']}/arquivo", headers=h)
    assert arq.status_code == 200
    assert arq.content == WEBP_FAKE

    # Cópia própria: apagar o arquivo da mensagem (retenção) não afeta a galeria.
    (tmp_path / nome_msg).unlink()
    assert client.get(f"/v1/whatsapp/figurinhas/{fig['id']}/arquivo", headers=h).status_code == 200

    rm = client.delete(f"/v1/whatsapp/figurinhas/{fig['id']}", headers=h)
    assert rm.status_code == 204
    assert client.get("/v1/whatsapp/figurinhas", headers=h).json() == []


def test_galeria_e_pessoal_por_atendente(client, seed_base, auth_headers, db_session, tmp_path, monkeypatch):
    chat, msg, _ = _chat_com_figurinha(db_session, seed_base, tmp_path, monkeypatch)
    r = client.post(
        "/v1/whatsapp/figurinhas/de-mensagem",
        json={"chat_id": chat.id, "mensagem_id": msg.id},
        headers=auth_headers["a1"],
    )
    fig_id = r.json()["id"]

    assert client.get("/v1/whatsapp/figurinhas", headers=auth_headers["admin"]).json() == []
    assert client.get(f"/v1/whatsapp/figurinhas/{fig_id}/arquivo", headers=auth_headers["admin"]).status_code == 404
    assert client.delete(f"/v1/whatsapp/figurinhas/{fig_id}", headers=auth_headers["admin"]).status_code == 404
    assert len(client.get("/v1/whatsapp/figurinhas", headers=auth_headers["a1"]).json()) == 1


def test_salvar_exige_acesso_ao_chat_e_tipo_figurinha(client, seed_base, auth_headers, db_session, tmp_path, monkeypatch):
    chat, msg, _ = _chat_com_figurinha(db_session, seed_base, tmp_path, monkeypatch)
    outro_setor = client.post(
        "/v1/whatsapp/figurinhas/de-mensagem",
        json={"chat_id": chat.id, "mensagem_id": msg.id},
        headers=auth_headers["a2"],
    )
    assert outro_setor.status_code == 403

    msg.tipo_midia = "imagem"
    db_session.commit()
    imagem = client.post(
        "/v1/whatsapp/figurinhas/de-mensagem",
        json={"chat_id": chat.id, "mensagem_id": msg.id},
        headers=auth_headers["a1"],
    )
    assert imagem.status_code == 404
