from __future__ import annotations

from app.models.whatsapp_chat import WhatsappChat, WhatsappMensagem, WhatsappSettings
from app.services.whatsapp_avaliacao import (
    mensagem_oculta_na_conversa,
    parse_nota_avaliacao,
    processar_resposta_avaliacao,
)


def test_parse_nota_avaliacao():
    assert parse_nota_avaliacao("5") == 5
    assert parse_nota_avaliacao(" 3 ") == 3
    assert parse_nota_avaliacao("0") is None
    assert parse_nota_avaliacao("6") is None
    assert parse_nota_avaliacao("ótimo") is None


def test_mensagens_avaliacao_ocultas_na_conversa():
    assert mensagem_oculta_na_conversa("auto_avaliacao_solicitacao")
    assert mensagem_oculta_na_conversa("avaliacao_cliente_nota")
    assert not mensagem_oculta_na_conversa("auto_encerrado")
    assert not mensagem_oculta_na_conversa(None)


def _configurar(db_session, *, avaliacao_ativa: bool = True):
    st = WhatsappSettings(
        evolution_base_url="http://evolution.test",
        evolution_instance_name="inst",
        evolution_api_key="key",
        avaliacao_ativa=avaliacao_ativa,
        auto_msg_avaliacao_ativa=True,
        auto_msg_encerrado_ativa=True,
    )
    db_session.add(st)
    db_session.commit()
    return st


def test_encerrar_com_avaliacao_ativa_vai_para_aguardando_avaliacao(
    client, seed_base, auth_headers, db_session, monkeypatch
):
    _configurar(db_session)
    client.patch(
        "/v1/settings/whatsapp",
        json={"webhook_secret": "avaliacao-1"},
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": "avaliacao-1"}
    body = {
        "event": "messages.upsert",
        "data": {
            "messages": [
                {
                    "key": {"remoteJid": "5511888777666@s.whatsapp.net", "fromMe": False, "id": "m-av-1"},
                    "message": {"conversation": "Oi"},
                }
            ]
        },
    }
    client.post("/v1/webhooks/evolution", json=body, headers=h)
    fila = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"]).json()
    cid = fila[0]["id"]
    client.post(f"/v1/whatsapp/chats/{cid}/assumir", headers=auth_headers["a1"])

    enviados: list[str] = []

    def fake_send(base, inst, key, wa, text):
        enviados.append(text)
        return True, None, "wa-out-av"

    monkeypatch.setattr("app.services.whatsapp_avaliacao.evolution_api.evolution_send_text", fake_send)

    r = client.post(f"/v1/whatsapp/chats/{cid}/encerrar", headers=auth_headers["a1"])
    assert r.status_code == 200
    data = r.json()
    assert data["estado"] == "aguardando_avaliacao"
    assert data["encerramento_at"] is not None
    assert data.get("avaliacao_nota") is None
    assert len(enviados) >= 1
    assert "1" in enviados[0] and "5" in enviados[0]


def test_resposta_nota_encerra_chat(client, seed_base, auth_headers, db_session, monkeypatch):
    st = _configurar(db_session)
    chat = WhatsappChat(
        protocolo="WPP-AV-1",
        wa_id="5511999112233",
        cliente_nome="Cliente",
        estado="aguardando_avaliacao",
        atendente_id=1,
        avaliacao_solicitada=True,
    )
    db_session.add(chat)
    db_session.commit()

    monkeypatch.setattr(
        "app.services.whatsapp_avaliacao.evolution_api.evolution_send_text",
        lambda *_a, **_k: (True, None, "wa-out-thx"),
    )

    msg = WhatsappMensagem(
        chat_id=chat.id,
        direcao="inbound",
        corpo="4",
        tipo_midia="texto",
    )
    db_session.add(msg)
    processar_resposta_avaliacao(db_session, chat, st, "4", msg_inbound=msg)
    db_session.commit()
    db_session.refresh(chat)

    assert chat.estado == "encerrado"
    assert chat.avaliacao_nota == 4
    assert chat.avaliacao_respondida_at is not None
    assert msg.evento_sistema == "avaliacao_cliente_nota"


def test_resposta_invalida_encerra_sem_avaliacao(client, seed_base, auth_headers, db_session, monkeypatch):
    """API legada: encerrar_avaliacao_sem_nota com motivo invalida."""
    from app.services.whatsapp_avaliacao import encerrar_avaliacao_sem_nota

    st = _configurar(db_session)
    chat = WhatsappChat(
        protocolo="WPP-AV-2",
        wa_id="5511999223344",
        cliente_nome="Cliente",
        estado="aguardando_avaliacao",
        atendente_id=1,
        avaliacao_solicitada=True,
    )
    db_session.add(chat)
    db_session.commit()

    enviados: list[str] = []

    def fake_send(base, inst, key, wa, text):
        enviados.append(text)
        return True, None, "wa-out-x"

    monkeypatch.setattr("app.services.whatsapp_avaliacao.evolution_api.evolution_send_text", fake_send)

    msg = WhatsappMensagem(chat_id=chat.id, direcao="inbound", corpo="ótimo", tipo_midia="texto")
    db_session.add(msg)
    encerrar_avaliacao_sem_nota(db_session, chat, st, motivo="invalida", msg_inbound=msg)
    db_session.commit()
    db_session.refresh(chat)

    assert chat.estado == "encerrado"
    assert chat.avaliacao_nota is None
    assert msg.evento_sistema == "avaliacao_cliente_invalida"
    assert enviados
    assert "sem avaliação" in enviados[0].lower() or "encerrado" in enviados[0].lower()


def test_processar_nao_nota_nao_altera_chat(client, seed_base, auth_headers, db_session, monkeypatch):
    st = _configurar(db_session)
    chat = WhatsappChat(
        protocolo="WPP-AV-2b",
        wa_id="5511999223355",
        estado="aguardando_avaliacao",
        atendente_id=1,
        avaliacao_solicitada=True,
    )
    db_session.add(chat)
    db_session.commit()
    monkeypatch.setattr(
        "app.services.whatsapp_avaliacao.evolution_api.evolution_send_text",
        lambda *_a, **_k: (True, None, "x"),
    )
    assert processar_resposta_avaliacao(db_session, chat, st, "ótimo") == "nao_nota"
    db_session.refresh(chat)
    assert chat.estado == "aguardando_avaliacao"


def test_webhook_texto_nao_nota_abre_chat_novo(client, seed_base, auth_headers, db_session, monkeypatch):
    """#598 — texto que não é nota encerra avaliação e abre atendimento com a mensagem."""
    from datetime import datetime, timezone

    from tests.test_whatsapp_chats import _webhook_body

    _configurar(db_session)
    monkeypatch.setattr(
        "app.services.whatsapp_avaliacao.evolution_api.evolution_send_text",
        lambda *_a, **_k: (True, None, "wa-pular"),
    )
    monkeypatch.setattr(
        "app.api.whatsapp_webhook.evolution_api.evolution_send_text",
        lambda *_a, **_k: (True, None, "wa-espera"),
    )
    wa = "5511999000598"
    antigo = WhatsappChat(
        protocolo="WPP-AV-598-A",
        wa_id=wa,
        estado="aguardando_avaliacao",
        atendente_id=seed_base["a1"].id,
        avaliacao_solicitada=True,
        encerramento_at=datetime.now(timezone.utc),
    )
    db_session.add(antigo)
    db_session.commit()
    antigo_id = antigo.id
    db_session.close()

    client.patch(
        "/v1/settings/whatsapp",
        json={"webhook_secret": "av-598-pular", "auto_msg_espera_ativa": False, "auto_msg_fora_horario_ativa": False},
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": "av-598-pular"}
    r = client.post(
        "/v1/webhooks/evolution",
        json=_webhook_body(wa_id=wa, msg_id="598-nao-nota", text="Preciso de ajuda de novo"),
        headers=h,
    )
    assert r.status_code == 200, r.text

    db_session.expire_all()
    antigo2 = db_session.query(WhatsappChat).filter(WhatsappChat.id == antigo_id).first()
    assert antigo2 is not None
    assert antigo2.estado == "encerrado"
    assert antigo2.avaliacao_nota is None

    novos = (
        db_session.query(WhatsappChat)
        .filter(
            WhatsappChat.wa_id == wa,
            WhatsappChat.estado == "aguardando_atendente",
        )
        .all()
    )
    assert len(novos) == 1
    msgs = (
        db_session.query(WhatsappMensagem)
        .filter(
            WhatsappMensagem.chat_id == novos[0].id,
            WhatsappMensagem.direcao == "inbound",
        )
        .all()
    )
    assert len(msgs) == 1
    assert msgs[0].corpo == "Preciso de ajuda de novo"


def test_timeout_avaliacao_encerra_chat(client, seed_base, auth_headers, db_session, monkeypatch):
    """#598 — após a janela, job finaliza aguardando_avaliacao."""
    from datetime import datetime, timedelta, timezone

    from app.services.whatsapp_avaliacao import process_whatsapp_avaliacao_timeouts

    st = _configurar(db_session)
    st.avaliacao_janela_minutos = 30
    db_session.commit()

    enviados: list[str] = []

    def fake_send(base, inst, key, wa, text):
        enviados.append(text)
        return True, None, "wa-timeout"

    monkeypatch.setattr("app.services.whatsapp_avaliacao.evolution_api.evolution_send_text", fake_send)

    chat = WhatsappChat(
        protocolo="WPP-AV-TO",
        wa_id="5511999000599",
        estado="aguardando_avaliacao",
        atendente_id=seed_base["a1"].id,
        avaliacao_solicitada=True,
        encerramento_at=datetime.now(timezone.utc) - timedelta(minutes=31),
    )
    db_session.add(chat)
    db_session.commit()

    n = process_whatsapp_avaliacao_timeouts(db_session, limit=50)
    assert n == 1
    db_session.refresh(chat)
    assert chat.estado == "encerrado"
    assert chat.avaliacao_nota is None
    assert enviados
    assert "período" in enviados[0].lower() or "encerrou" in enviados[0].lower() or "nova mensagem" in enviados[0].lower()


def test_inbound_apos_timeout_abre_chat_novo(client, seed_base, auth_headers, db_session, monkeypatch):
    """#598 — após timeout, próxima mensagem abre atendimento novo."""
    from datetime import datetime, timezone

    from tests.test_whatsapp_chats import _webhook_body

    _configurar(db_session)
    monkeypatch.setattr(
        "app.api.whatsapp_webhook.evolution_api.evolution_send_text",
        lambda *_a, **_k: (True, None, "wa-esp"),
    )
    wa = "5511999000600"
    db_session.add(
        WhatsappChat(
            protocolo="WPP-AV-POS-TO",
            wa_id=wa,
            estado="encerrado",
            atendente_id=seed_base["a1"].id,
            avaliacao_solicitada=True,
            encerramento_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()
    db_session.close()

    client.patch(
        "/v1/settings/whatsapp",
        json={"webhook_secret": "av-598-pos", "auto_msg_espera_ativa": False, "auto_msg_fora_horario_ativa": False},
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": "av-598-pos"}
    r = client.post(
        "/v1/webhooks/evolution",
        json=_webhook_body(wa_id=wa, msg_id="598-pos-to", text="Oi de novo"),
        headers=h,
    )
    assert r.status_code == 200
    fila = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"]).json()
    assert any(c.get("wa_id") == wa for c in fila)


def test_mensagens_avaliacao_nao_aparecem_na_conversa(client, seed_base, auth_headers, db_session):
    _configurar(db_session)
    aid = seed_base["a1"].id
    chat = WhatsappChat(
        protocolo="WPP-AV-3",
        wa_id="5511999334455",
        cliente_nome="Cliente",
        estado="encerrado",
        atendente_id=aid,
        avaliacao_solicitada=True,
        avaliacao_nota=5,
    )
    db_session.add(chat)
    db_session.flush()
    db_session.add_all(
        [
            WhatsappMensagem(
                chat_id=chat.id,
                direcao="outbound",
                corpo="[ BOT ]: Avalie",
                tipo_midia="texto",
                evento_sistema="auto_avaliacao_solicitacao",
            ),
            WhatsappMensagem(
                chat_id=chat.id,
                direcao="inbound",
                corpo="5",
                tipo_midia="texto",
                evento_sistema="avaliacao_cliente_nota",
            ),
            WhatsappMensagem(
                chat_id=chat.id,
                direcao="outbound",
                corpo="[ Atendente ]: Olá",
                tipo_midia="texto",
                atendente_id=aid,
            ),
        ]
    )
    db_session.commit()

    r = client.get(f"/v1/whatsapp/chats/{chat.id}/mensagens", headers=auth_headers["a1"])
    assert r.status_code == 200
    corpos = [m["corpo"] for m in r.json()]
    assert len(corpos) == 1
    assert "Olá" in corpos[0]


def test_listar_avaliacoes_admin(client, seed_base, auth_headers, db_session):
    _configurar(db_session)
    chat = WhatsappChat(
        protocolo="WPP-AV-4",
        wa_id="5511999445566",
        cliente_nome="Cliente",
        estado="encerrado",
        atendente_id=1,
        avaliacao_solicitada=True,
        avaliacao_nota=3,
    )
    db_session.add(chat)
    db_session.commit()

    r = client.get("/v1/whatsapp/chats/avaliacoes", headers=auth_headers["admin"])
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert body["items"][0]["nota"] == 3

    r403 = client.get("/v1/whatsapp/chats/avaliacoes", headers=auth_headers["a1"])
    assert r403.status_code == 403


def test_historico_inclui_aguardando_avaliacao(client, seed_base, auth_headers, db_session, monkeypatch):
    """#448 — sessão aguardando avaliação aparece no histórico (filtro padrão)."""
    _configurar(db_session)
    client.patch(
        "/v1/settings/whatsapp",
        json={"webhook_secret": "hist-av"},
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": "hist-av"}
    body = {
        "event": "messages.upsert",
        "data": {
            "messages": [
                {
                    "key": {"remoteJid": "5511777666555@s.whatsapp.net", "fromMe": False, "id": "hist-av-1"},
                    "message": {"conversation": "Oi"},
                }
            ]
        },
    }
    client.post("/v1/webhooks/evolution", json=body, headers=h)
    cid = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"]).json()[0]["id"]
    client.post(f"/v1/whatsapp/chats/{cid}/assumir", headers=auth_headers["a1"])
    monkeypatch.setattr(
        "app.services.whatsapp_avaliacao.evolution_api.evolution_send_text",
        lambda *_a, **_k: (True, None, "wa-out-hist"),
    )
    enc = client.post(f"/v1/whatsapp/chats/{cid}/encerrar", headers=auth_headers["a1"])
    assert enc.json()["estado"] == "aguardando_avaliacao"

    hist = client.get("/v1/whatsapp/chats/encerrados", headers=auth_headers["admin"]).json()
    assert any(item["id"] == cid for item in hist["items"])
    assert any(item["estado"] == "aguardando_avaliacao" for item in hist["items"] if item["id"] == cid)

    so_encerrado = client.get("/v1/whatsapp/chats/encerrados?estado=encerrado", headers=auth_headers["admin"]).json()
    assert not any(item["id"] == cid for item in so_encerrado["items"])


def test_avaliacoes_exclui_sem_nota_por_defeito(client, seed_base, auth_headers, db_session):
    """#448 — aba Avaliações lista só chats com nota respondida."""
    _configurar(db_session)
    db_session.add(
        WhatsappChat(
            protocolo="WPP-AV-SEM",
            wa_id="5511999000011",
            cliente_nome="Sem nota",
            estado="aguardando_avaliacao",
            atendente_id=1,
            avaliacao_solicitada=True,
            avaliacao_nota=None,
        )
    )
    db_session.add(
        WhatsappChat(
            protocolo="WPP-AV-COM",
            wa_id="5511999000022",
            cliente_nome="Com nota",
            estado="encerrado",
            atendente_id=1,
            avaliacao_solicitada=True,
            avaliacao_nota=5,
        )
    )
    db_session.commit()

    body = client.get("/v1/whatsapp/chats/avaliacoes", headers=auth_headers["admin"]).json()
    ids = [item["chat_id"] for item in body["items"]]
    assert any(item["nota"] == 5 for item in body["items"])
    assert all(item.get("nota") is not None for item in body["items"])
    assert not any(item.get("sem_avaliacao") for item in body["items"])

    audit = client.get(
        "/v1/whatsapp/chats/avaliacoes?incluir_sem_resposta=true",
        headers=auth_headers["admin"],
    ).json()
    assert any(item.get("sem_avaliacao") for item in audit["items"])

