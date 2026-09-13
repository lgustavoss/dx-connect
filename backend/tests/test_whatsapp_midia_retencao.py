"""Retenção de mídia WhatsApp e fallback Evolution (#899 / #900 / #901)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.whatsapp_chat import WhatsappChat, WhatsappMensagem, WhatsappSettings
from app.services import whatsapp_media_retencao as retencao
from app.services.whatsapp_media_storage import gravar_bytes_em_disco


PNG_MIN = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05"
    b"\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _chat_com_imagem(db_session, seed_base, tmp_path, monkeypatch, *, created_at=None, wa_mid="wa-ret-1"):
    monkeypatch.setattr("app.config.settings.WHATSAPP_MEDIA_DIR", str(tmp_path))
    monkeypatch.setattr("app.services.whatsapp_media_storage.settings.WHATSAPP_MEDIA_DIR", str(tmp_path))
    nome = gravar_bytes_em_disco(PNG_MIN, "image/png")
    assert nome
    chat = WhatsappChat(
        protocolo="RET-MIDIA-899",
        wa_id="5511999000899",
        cliente_nome="Cliente mídia",
        estado="em_atendimento",
        setor_id=seed_base["setor1"].id,
        atendente_id=seed_base["a1"].id,
        atendimento_inicio_at=datetime.now(timezone.utc),
    )
    db_session.add(chat)
    db_session.flush()
    agora = created_at or datetime.now(timezone.utc)
    msg = WhatsappMensagem(
        chat_id=chat.id,
        direcao="inbound",
        corpo="Foto",
        tipo_midia="imagem",
        mimetype="image/png",
        midia_nome_arquivo=nome,
        midia_nome_original="foto.png",
        wa_message_id=wa_mid,
        midia_estado=retencao.MIDIA_ATIVA,
        created_at=agora,
    )
    db_session.add(msg)
    db_session.commit()
    db_session.refresh(msg)
    db_session.refresh(chat)
    return chat, msg, nome


def test_job_expira_arquivo_e_preserva_metadados(db_session, seed_base, tmp_path, monkeypatch):
    velho = datetime.now(timezone.utc) - timedelta(days=120)
    chat, msg, nome = _chat_com_imagem(db_session, seed_base, tmp_path, monkeypatch, created_at=velho)
    caminho = tmp_path / nome
    assert caminho.is_file()

    out = retencao.processar_expiracao_midias(db_session, limit=50)
    db_session.commit()
    db_session.refresh(msg)

    assert out["removidas"] == 1
    assert not caminho.is_file()
    assert msg.midia_estado == retencao.MIDIA_EXPIRADA_LOCAL
    assert msg.midia_nome_arquivo == nome
    assert msg.corpo == "Foto"
    assert msg.wa_message_id == "wa-ret-1"
    assert msg.mimetype == "image/png"


def test_job_nao_expira_midia_recente(db_session, seed_base, tmp_path, monkeypatch):
    chat, msg, nome = _chat_com_imagem(db_session, seed_base, tmp_path, monkeypatch)
    caminho = tmp_path / nome
    out = retencao.processar_expiracao_midias(db_session, limit=50)
    db_session.commit()
    db_session.refresh(msg)
    assert out["removidas"] == 0
    assert caminho.is_file()
    assert msg.midia_estado == retencao.MIDIA_ATIVA


def test_get_midia_expirada_reidrata_via_evolution(
    client, seed_base, auth_headers, db_session, tmp_path, monkeypatch
):
    velho = datetime.now(timezone.utc) - timedelta(days=120)
    chat, msg, nome = _chat_com_imagem(db_session, seed_base, tmp_path, monkeypatch, created_at=velho)
    retencao.processar_expiracao_midias(db_session, limit=50)
    db_session.commit()

    st = WhatsappSettings(
        evolution_base_url="http://evolution.test",
        evolution_instance_name="inst",
        evolution_api_key="key-test",
    )
    db_session.add(st)
    db_session.commit()

    import base64

    b64 = base64.b64encode(PNG_MIN).decode("ascii")

    def fake_get(_base, _inst, _key, envelope, *, convert_to_mp4=False, timeout=90):
        assert envelope.get("key", {}).get("id") == "wa-ret-1"
        return True, b64, None

    monkeypatch.setattr(
        "app.services.whatsapp_media_retencao.evolution_api.evolution_get_base64_from_media_message",
        fake_get,
    )

    r = client.get(
        f"/v1/whatsapp/chats/{chat.id}/mensagens/{msg.id}/midia",
        headers=auth_headers["a1"],
    )
    assert r.status_code == 200
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"
    db_session.refresh(msg)
    assert msg.midia_estado == retencao.MIDIA_ATIVA
    assert msg.midia_nome_arquivo != nome
    assert (tmp_path / msg.midia_nome_arquivo).is_file()


def test_get_midia_expirada_evolution_falha_retorna_410(
    client, seed_base, auth_headers, db_session, tmp_path, monkeypatch
):
    velho = datetime.now(timezone.utc) - timedelta(days=120)
    chat, msg, _nome = _chat_com_imagem(
        db_session, seed_base, tmp_path, monkeypatch, created_at=velho, wa_mid="wa-gone"
    )
    retencao.processar_expiracao_midias(db_session, limit=50)
    db_session.commit()

    db_session.add(
        WhatsappSettings(
            evolution_base_url="http://evolution.test",
            evolution_instance_name="inst",
            evolution_api_key="key-test",
        )
    )
    db_session.commit()

    monkeypatch.setattr(
        "app.services.whatsapp_media_retencao.evolution_api.evolution_get_base64_from_media_message",
        lambda *_a, **_k: (False, None, "Message not found"),
    )

    r = client.get(
        f"/v1/whatsapp/chats/{chat.id}/mensagens/{msg.id}/midia",
        headers=auth_headers["a1"],
    )
    assert r.status_code == 410
    body = r.json()
    assert body["codigo"] == "midia_indisponivel"
    assert "não está mais disponível" in body["detail"]
    db_session.refresh(msg)
    assert msg.midia_estado == retencao.MIDIA_INDISPONIVEL

    rows = client.get(f"/v1/whatsapp/chats/{chat.id}/mensagens", headers=auth_headers["a1"]).json()
    last = next(x for x in rows if x["id"] == msg.id)
    assert last["midia_disponivel"] is False
    assert last["midia_estado"] == retencao.MIDIA_INDISPONIVEL
    assert last["corpo"] == "Foto"


def test_get_midia_timeout_evolution_nao_marca_indisponivel(
    client, seed_base, auth_headers, db_session, tmp_path, monkeypatch
):
    velho = datetime.now(timezone.utc) - timedelta(days=120)
    chat, msg, _nome = _chat_com_imagem(
        db_session, seed_base, tmp_path, monkeypatch, created_at=velho, wa_mid="wa-timeout"
    )
    retencao.processar_expiracao_midias(db_session, limit=50)
    db_session.commit()

    db_session.add(
        WhatsappSettings(
            evolution_base_url="http://evolution.test",
            evolution_instance_name="inst",
            evolution_api_key="key-test",
        )
    )
    db_session.commit()

    monkeypatch.setattr(
        "app.services.whatsapp_media_retencao.evolution_api.evolution_get_base64_from_media_message",
        lambda *_a, **_k: (False, None, "timed out"),
    )

    r = client.get(
        f"/v1/whatsapp/chats/{chat.id}/mensagens/{msg.id}/midia",
        headers=auth_headers["a1"],
    )
    assert r.status_code == 503
    body = r.json()
    assert body["codigo"] == "midia_temporariamente_indisponivel"
    db_session.refresh(msg)
    assert msg.midia_estado == retencao.MIDIA_EXPIRADA_LOCAL

    r2 = client.get(
        f"/v1/whatsapp/chats/{chat.id}/mensagens/{msg.id}/midia",
        headers=auth_headers["a1"],
    )
    assert r2.status_code == 503


def test_get_midia_410_nao_quebra_listagem(client, seed_base, auth_headers, db_session, tmp_path, monkeypatch):
    chat, msg, _nome = _chat_com_imagem(db_session, seed_base, tmp_path, monkeypatch, wa_mid="")
    msg.midia_nome_arquivo = None
    msg.midia_estado = retencao.MIDIA_INDISPONIVEL
    db_session.commit()
    r = client.get(
        f"/v1/whatsapp/chats/{chat.id}/mensagens/{msg.id}/midia",
        headers=auth_headers["a1"],
    )
    assert r.status_code == 410
    lista = client.get(f"/v1/whatsapp/chats/{chat.id}/mensagens", headers=auth_headers["a1"])
    assert lista.status_code == 200


def test_settings_retencao_admin_e_403_atendente(client, seed_base, auth_headers):
    r403 = client.patch(
        "/v1/settings/whatsapp",
        json={"midia_retencao_dias_video": 15},
        headers=auth_headers["a1"],
    )
    assert r403.status_code == 403
    ok = client.patch(
        "/v1/settings/whatsapp",
        json={"midia_retencao_dias_video": 15, "midia_retencao_dias_imagem": 60},
        headers=auth_headers["admin"],
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["midia_retencao_dias_video"] == 15
    assert body["midia_retencao_dias_imagem"] == 60
