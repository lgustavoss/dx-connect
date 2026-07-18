from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.whatsapp_chat import WhatsappChat, WhatsappMensagem, WhatsappSettings
from app.services.whatsapp_inactivity_worker import process_whatsapp_inactivity_closures


def _configurar_evolution(db_session):
    st = WhatsappSettings(
        evolution_base_url="http://evolution.test",
        evolution_instance_name="inst",
        evolution_api_key="key",
        webhook_secret="sec",
        inativ_encerramento_ativa=True,
        inativ_aviso_minutos=10,
        inativ_encerramento_apos_aviso_minutos=5,
        auto_msg_inativ_aviso_ativa=True,
        auto_msg_encerrado_ativa=True,
    )
    db_session.add(st)
    db_session.commit()


def _chat_em_atendimento(db_session, *, wa_id: str = "5511999887766", atendente_id: int = 1) -> WhatsappChat:
    chat = WhatsappChat(
        protocolo="WPP-TEST-1",
        wa_id=wa_id,
        cliente_nome="Cliente Teste",
        estado="em_atendimento",
        atendente_id=atendente_id,
    )
    db_session.add(chat)
    db_session.flush()
    return chat


def test_settings_exige_minutos_quando_inatividade_ativa(client, seed_base, auth_headers):
    r = client.patch(
        "/v1/settings/whatsapp",
        json={"inativ_encerramento_ativa": True, "inativ_aviso_minutos": 10},
        headers=auth_headers["admin"],
    )
    assert r.status_code == 400


def test_worker_envia_aviso_apos_inatividade(client, seed_base, auth_headers, db_session, monkeypatch):
    _configurar_evolution(db_session)
    chat = _chat_em_atendimento(db_session)
    antiga_cliente = datetime.now(timezone.utc) - timedelta(minutes=20)
    antiga_atendente = datetime.now(timezone.utc) - timedelta(minutes=15)
    db_session.add(
        WhatsappMensagem(
            chat_id=chat.id,
            direcao="inbound",
            corpo="Preciso de ajuda",
            tipo_midia="texto",
            created_at=antiga_cliente,
        )
    )
    db_session.add(
        WhatsappMensagem(
            chat_id=chat.id,
            direcao="outbound",
            corpo="[ Atendente ]: Alguma dúvida?",
            tipo_midia="texto",
            atendente_id=1,
            created_at=antiga_atendente,
        )
    )
    db_session.commit()

    enviados: list[str] = []

    def fake_send(base, inst, key, wa, text):
        enviados.append(text)
        return True, None, "wa-out-1"

    monkeypatch.setattr(
        "app.services.whatsapp_inactivity_worker.evolution_api.evolution_send_text",
        fake_send,
    )

    n = process_whatsapp_inactivity_closures(db_session)
    db_session.commit()

    assert n == 1
    assert len(enviados) == 1
    assert "sem responder" in enviados[0].lower() or "encerr" in enviados[0].lower()
    aviso = (
        db_session.query(WhatsappMensagem)
        .filter(WhatsappMensagem.chat_id == chat.id, WhatsappMensagem.evento_sistema == "auto_inativ_aviso")
        .first()
    )
    assert aviso is not None
    assert chat.estado == "em_atendimento"


def test_worker_encerra_apos_aviso(client, seed_base, auth_headers, db_session, monkeypatch):
    _configurar_evolution(db_session)
    chat = _chat_em_atendimento(db_session, wa_id="5511999776655")
    antiga_aviso = datetime.now(timezone.utc) - timedelta(minutes=8)
    db_session.add(
        WhatsappMensagem(
            chat_id=chat.id,
            direcao="outbound",
            corpo="[ BOT ]: Aviso de encerramento",
            tipo_midia="texto",
            evento_sistema="auto_inativ_aviso",
            created_at=antiga_aviso,
        )
    )
    db_session.commit()

    monkeypatch.setattr(
        "app.services.whatsapp_inactivity_worker.evolution_api.evolution_send_text",
        lambda *_a, **_k: (True, None, "wa-out-2"),
    )

    n = process_whatsapp_inactivity_closures(db_session)
    db_session.commit()
    db_session.refresh(chat)

    assert n == 1
    assert chat.estado == "encerrado"
    assert chat.encerramento_at is not None
    assert chat.classificacao_demanda_pendente is True
    marco = (
        db_session.query(WhatsappMensagem)
        .filter(
            WhatsappMensagem.chat_id == chat.id,
            WhatsappMensagem.evento_sistema == "auto_encerrado_inatividade",
        )
        .first()
    )
    assert marco is not None


def test_pode_registrar_demanda_apos_encerramento_inatividade(
    client, seed_base, auth_headers, db_session, monkeypatch
):
    from app.models.ticket_classificacao import TicketMotivo, TicketNatureza

    _configurar_evolution(db_session)
    a1_id = seed_base["a1"].id
    chat = _chat_em_atendimento(db_session, wa_id="5511999112233", atendente_id=a1_id)
    antiga_aviso = datetime.now(timezone.utc) - timedelta(minutes=8)
    db_session.add(
        WhatsappMensagem(
            chat_id=chat.id,
            direcao="outbound",
            corpo="[ BOT ]: Aviso",
            tipo_midia="texto",
            evento_sistema="auto_inativ_aviso",
            created_at=antiga_aviso,
        )
    )
    nat = TicketNatureza(nome="Nat Inativ", slug="nat-inativ-test", ordem=1, ativo=True)
    db_session.add(nat)
    db_session.flush()
    mot = TicketMotivo(natureza_id=nat.id, nome="Mot Inativ", slug="mot-inativ-test", ordem=1, ativo=True)
    db_session.add(mot)
    db_session.commit()

    monkeypatch.setattr(
        "app.services.whatsapp_inactivity_worker.evolution_api.evolution_send_text",
        lambda *_a, **_k: (True, None, "wa-out-dem"),
    )
    process_whatsapp_inactivity_closures(db_session)
    db_session.commit()
    db_session.refresh(chat)
    assert chat.estado == "encerrado"

    r = client.post(
        f"/v1/whatsapp/chats/{chat.id}/demandas",
        json={"natureza_id": nat.id, "motivo_id": mot.id, "descricao_curta": "Pós-inatividade"},
        headers=auth_headers["a1"],
    )
    assert r.status_code == 201, r.text
    assert r.json()["descricao_curta"] == "Pós-inatividade"
    db_session.refresh(chat)
    assert chat.classificacao_demanda_pendente is False


def test_concluir_classificacao_sem_demanda(client, seed_base, auth_headers, db_session, monkeypatch):
    _configurar_evolution(db_session)
    a1_id = seed_base["a1"].id
    chat = _chat_em_atendimento(db_session, wa_id="5511999223344", atendente_id=a1_id)
    antiga_aviso = datetime.now(timezone.utc) - timedelta(minutes=8)
    db_session.add(
        WhatsappMensagem(
            chat_id=chat.id,
            direcao="outbound",
            corpo="[ BOT ]: Aviso",
            tipo_midia="texto",
            evento_sistema="auto_inativ_aviso",
            created_at=antiga_aviso,
        )
    )
    db_session.commit()
    monkeypatch.setattr(
        "app.services.whatsapp_inactivity_worker.evolution_api.evolution_send_text",
        lambda *_a, **_k: (True, None, "wa-out-cls"),
    )
    process_whatsapp_inactivity_closures(db_session)
    db_session.commit()
    db_session.refresh(chat)
    assert chat.classificacao_demanda_pendente is True

    meus = client.get("/v1/whatsapp/chats/meus", headers=auth_headers["a1"]).json()
    assert any(c["id"] == chat.id and c.get("classificacao_demanda_pendente") for c in meus)

    r = client.post(
        f"/v1/whatsapp/chats/{chat.id}/classificacao-demanda/concluir",
        headers=auth_headers["a1"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["classificacao_demanda_pendente"] is False
    db_session.refresh(chat)
    assert chat.classificacao_demanda_pendente is False


def test_inbound_abre_chat_novo_quando_pendente_classificacao(
    client, seed_base, auth_headers, db_session, monkeypatch
):
    """Cliente manda mensagem nova: chat a classificar permanece; abre atendimento novo."""
    from tests.test_whatsapp_chats import _webhook_body

    _configurar_evolution(db_session)
    a1_id = seed_base["a1"].id
    wa = "5511888001122"
    chat = _chat_em_atendimento(db_session, wa_id=wa, atendente_id=a1_id)
    antiga_aviso = datetime.now(timezone.utc) - timedelta(minutes=8)
    db_session.add(
        WhatsappMensagem(
            chat_id=chat.id,
            direcao="outbound",
            corpo="[ BOT ]: Aviso",
            tipo_midia="texto",
            evento_sistema="auto_inativ_aviso",
            created_at=antiga_aviso,
        )
    )
    db_session.commit()
    monkeypatch.setattr(
        "app.services.whatsapp_inactivity_worker.evolution_api.evolution_send_text",
        lambda *_a, **_k: (True, None, "wa-out-new"),
    )
    # Também mock envio de auto_espera no webhook (ids únicos — uq wa_message_id)
    _wa_seq = {"n": 0}

    def _fake_send(*_a, **_k):
        _wa_seq["n"] += 1
        return True, None, f"wa-espera-{_wa_seq['n']}"

    monkeypatch.setattr(
        "app.api.whatsapp_webhook.evolution_api.evolution_send_text",
        _fake_send,
    )
    process_whatsapp_inactivity_closures(db_session)
    db_session.commit()
    db_session.refresh(chat)
    assert chat.classificacao_demanda_pendente is True
    pendente_id = chat.id
    # Libera a conexão StaticPool antes do TestClient (outra Session no mesmo SQLite).
    db_session.close()

    client.patch(
        "/v1/settings/whatsapp",
        json={"webhook_secret": "sec-pendente-novo"},
        headers=auth_headers["admin"],
    )
    h = {"X-Dx-Webhook-Secret": "sec-pendente-novo"}
    r = client.post(
        "/v1/webhooks/evolution",
        json=_webhook_body(wa_id=wa, msg_id="msg-nova-pos-inativ", text="Oi de novo"),
        headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("processados", 0) >= 1, body

    fila = client.get("/v1/whatsapp/chats/fila", headers=auth_headers["a1"]).json()
    novos = [c for c in fila if c["wa_id"] == wa and c["id"] != pendente_id]
    assert len(novos) == 1, fila
    assert novos[0]["estado"] == "aguardando_atendente"
    assert novos[0].get("classificacao_demanda_pendente") is False

    meus = client.get("/v1/whatsapp/chats/meus", headers=auth_headers["a1"]).json()
    pendentes = [c for c in meus if c["id"] == pendente_id]
    assert len(pendentes) == 1, meus
    assert pendentes[0].get("classificacao_demanda_pendente") is True


def test_worker_nao_age_quando_ultima_mensagem_recente_do_cliente(
    client, seed_base, auth_headers, db_session, monkeypatch
):
    """Cliente falou há 1 min — silêncio ainda dentro do prazo."""
    _configurar_evolution(db_session)
    chat = _chat_em_atendimento(db_session, wa_id="5511999665544")
    antiga = datetime.now(timezone.utc) - timedelta(minutes=20)
    db_session.add(
        WhatsappMensagem(
            chat_id=chat.id,
            direcao="outbound",
            corpo="[ Atendente ]: Pergunta?",
            tipo_midia="texto",
            atendente_id=1,
            created_at=antiga,
        )
    )
    db_session.add(
        WhatsappMensagem(
            chat_id=chat.id,
            direcao="inbound",
            corpo="Resposta do cliente",
            tipo_midia="texto",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
    )
    db_session.commit()

    monkeypatch.setattr(
        "app.services.whatsapp_inactivity_worker.evolution_api.evolution_send_text",
        lambda *_a, **_k: (True, None, "wa-out-3"),
    )

    n = process_whatsapp_inactivity_closures(db_session)
    assert n == 0


def test_worker_nao_age_so_com_auto_assumido(client, seed_base, auth_headers, db_session, monkeypatch):
    """Mensagem de sistema ao assumir não conta como resposta do atendente."""
    _configurar_evolution(db_session)
    chat = _chat_em_atendimento(db_session, wa_id="5511888776655")
    antiga = datetime.now(timezone.utc) - timedelta(minutes=30)
    db_session.add(
        WhatsappMensagem(
            chat_id=chat.id,
            direcao="inbound",
            corpo="Preciso de ajuda",
            tipo_midia="texto",
            created_at=antiga,
        )
    )
    db_session.add(
        WhatsappMensagem(
            chat_id=chat.id,
            direcao="outbound",
            corpo="[ BOT ]: Atendimento iniciado",
            tipo_midia="texto",
            evento_sistema="auto_assumido",
            created_at=antiga + timedelta(minutes=1),
        )
    )
    db_session.commit()

    monkeypatch.setattr(
        "app.services.whatsapp_inactivity_worker.evolution_api.evolution_send_text",
        lambda *_a, **_k: (True, None, "wa-out-assumido"),
    )

    n = process_whatsapp_inactivity_closures(db_session)
    assert n == 0


def test_worker_nao_avisa_se_ultima_mensagem_recente(
    client, seed_base, auth_headers, db_session, monkeypatch
):
    """Última mensagem do atendente há 2 min reinicia o prazo — não avisa ainda."""
    _configurar_evolution(db_session)
    chat = _chat_em_atendimento(db_session, wa_id="5511999554433")
    t_cliente = datetime.now(timezone.utc) - timedelta(minutes=25)
    db_session.add(
        WhatsappMensagem(
            chat_id=chat.id,
            direcao="inbound",
            corpo="Oi",
            tipo_midia="texto",
            created_at=t_cliente,
        )
    )
    for i, delta in enumerate((20, 10, 2)):
        db_session.add(
            WhatsappMensagem(
                chat_id=chat.id,
                direcao="outbound",
                corpo=f"[ Atendente ]: Lembrete {i}",
                tipo_midia="texto",
                atendente_id=1,
                created_at=datetime.now(timezone.utc) - timedelta(minutes=delta),
            )
        )
    db_session.commit()

    monkeypatch.setattr(
        "app.services.whatsapp_inactivity_worker.evolution_api.evolution_send_text",
        lambda *_a, **_k: (True, None, "wa-out-4"),
    )

    n = process_whatsapp_inactivity_closures(db_session)
    assert n == 0


def test_worker_avisa_apos_silencio_desde_ultima_msg_atendente(
    client, seed_base, auth_headers, db_session, monkeypatch
):
    _configurar_evolution(db_session)
    chat = _chat_em_atendimento(db_session, wa_id="5511999554400")
    db_session.add(
        WhatsappMensagem(
            chat_id=chat.id,
            direcao="inbound",
            corpo="Oi",
            tipo_midia="texto",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=30),
        )
    )
    db_session.add(
        WhatsappMensagem(
            chat_id=chat.id,
            direcao="outbound",
            corpo="[ Atendente ]: Aguarde",
            tipo_midia="texto",
            atendente_id=1,
            created_at=datetime.now(timezone.utc) - timedelta(minutes=15),
        )
    )
    db_session.commit()

    monkeypatch.setattr(
        "app.services.whatsapp_inactivity_worker.evolution_api.evolution_send_text",
        lambda *_a, **_k: (True, None, "wa-out-silencio"),
    )

    n = process_whatsapp_inactivity_closures(db_session)
    assert n == 1


def test_worker_respeita_pausa_inatividade(client, seed_base, auth_headers, db_session, monkeypatch):
    _configurar_evolution(db_session)
    chat = _chat_em_atendimento(db_session, wa_id="5511999554411")
    chat.inatividade_pausada = True
    db_session.add(
        WhatsappMensagem(
            chat_id=chat.id,
            direcao="outbound",
            corpo="[ Atendente ]: Analisando",
            tipo_midia="texto",
            atendente_id=1,
            created_at=datetime.now(timezone.utc) - timedelta(minutes=30),
        )
    )
    db_session.commit()

    monkeypatch.setattr(
        "app.services.whatsapp_inactivity_worker.evolution_api.evolution_send_text",
        lambda *_a, **_k: (True, None, "wa-out-pausa"),
    )

    n = process_whatsapp_inactivity_closures(db_session)
    assert n == 0


def test_worker_nao_reenvia_aviso_duplicado_no_mesmo_ciclo(
    client, seed_base, auth_headers, db_session, monkeypatch
):
    """Vários workers Gunicorn não devem reenviar o aviso de inatividade."""
    _configurar_evolution(db_session)
    chat = _chat_em_atendimento(db_session, wa_id="5511999443322")
    antiga_cliente = datetime.now(timezone.utc) - timedelta(minutes=20)
    antiga_atendente = datetime.now(timezone.utc) - timedelta(minutes=15)
    db_session.add(
        WhatsappMensagem(
            chat_id=chat.id,
            direcao="inbound",
            corpo="Preciso de ajuda",
            tipo_midia="texto",
            created_at=antiga_cliente,
        )
    )
    db_session.add(
        WhatsappMensagem(
            chat_id=chat.id,
            direcao="outbound",
            corpo="[ Atendente ]: Alguma dúvida?",
            tipo_midia="texto",
            atendente_id=1,
            created_at=antiga_atendente,
        )
    )
    db_session.commit()

    enviados: list[str] = []

    def fake_send(base, inst, key, wa, text):
        enviados.append(text)
        return True, None, f"wa-out-dup-{len(enviados)}"

    monkeypatch.setattr(
        "app.services.whatsapp_inactivity_worker.evolution_api.evolution_send_text",
        fake_send,
    )

    n1 = process_whatsapp_inactivity_closures(db_session)
    db_session.commit()
    n2 = process_whatsapp_inactivity_closures(db_session)
    db_session.commit()

    assert n1 == 1
    assert n2 == 0
    assert len(enviados) == 1
    total_avisos = (
        db_session.query(WhatsappMensagem)
        .filter(WhatsappMensagem.chat_id == chat.id, WhatsappMensagem.evento_sistema == "auto_inativ_aviso")
        .count()
    )
    assert total_avisos == 1


def test_envio_mensagem_sai_da_pausa_inatividade(client, seed_base, auth_headers, db_session, monkeypatch):
    """Outbound humana do atendente limpa a pausa manual (reinicia o ciclo pelo timestamp da msg)."""
    _configurar_evolution(db_session)
    a1_id = seed_base["a1"].id
    chat = _chat_em_atendimento(db_session, wa_id="5511999554422", atendente_id=a1_id)
    chat.inatividade_pausada = True
    db_session.add(
        WhatsappMensagem(
            chat_id=chat.id,
            direcao="outbound",
            corpo="[ Atendente ]: Analisando",
            tipo_midia="texto",
            atendente_id=a1_id,
            created_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
    )
    db_session.commit()

    monkeypatch.setattr(
        "app.api.whatsapp_chats.evolution_api.evolution_send_text",
        lambda *_a, **_k: (True, None, "wa-out-despausa"),
    )

    r = client.post(
        f"/v1/whatsapp/chats/{chat.id}/mensagens",
        json={"texto": "Já resolvi"},
        headers=auth_headers["a1"],
    )
    assert r.status_code == 201, r.text
    db_session.refresh(chat)
    assert chat.inatividade_pausada is False
    assert chat.inatividade_retomada_em is None


def test_concluir_classificacao_com_demandas_existentes(
    client, seed_base, auth_headers, db_session, monkeypatch
):
    """Confirmar «manter demandas» pós-inatividade limpa o pendente (não fica preso na lista)."""
    from app.models.ticket_classificacao import TicketMotivo, TicketNatureza
    from app.models.whatsapp_chat_demanda import WhatsappChatDemanda

    _configurar_evolution(db_session)
    a1_id = seed_base["a1"].id
    chat = _chat_em_atendimento(db_session, wa_id="5511999554433", atendente_id=a1_id)
    antiga_aviso = datetime.now(timezone.utc) - timedelta(minutes=8)
    db_session.add(
        WhatsappMensagem(
            chat_id=chat.id,
            direcao="outbound",
            corpo="[ BOT ]: Aviso",
            tipo_midia="texto",
            evento_sistema="auto_inativ_aviso",
            created_at=antiga_aviso,
        )
    )
    nat = TicketNatureza(nome="Nat Manter", slug="nat-manter-inativ", ordem=1, ativo=True)
    db_session.add(nat)
    db_session.flush()
    mot = TicketMotivo(natureza_id=nat.id, nome="Mot Manter", slug="mot-manter-inativ", ordem=1, ativo=True)
    db_session.add(mot)
    db_session.flush()
    db_session.add(
        WhatsappChatDemanda(
            chat_id=chat.id,
            atendente_id=a1_id,
            natureza_id=nat.id,
            motivo_id=mot.id,
            descricao_curta="Já registada na sessão",
            desfecho="resolvido_sessao",
        )
    )
    db_session.commit()

    monkeypatch.setattr(
        "app.services.whatsapp_inactivity_worker.evolution_api.evolution_send_text",
        lambda *_a, **_k: (True, None, "wa-out-manter"),
    )
    process_whatsapp_inactivity_closures(db_session)
    db_session.commit()
    db_session.refresh(chat)
    assert chat.classificacao_demanda_pendente is True

    r = client.post(
        f"/v1/whatsapp/chats/{chat.id}/classificacao-demanda/concluir",
        headers=auth_headers["a1"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["classificacao_demanda_pendente"] is False
    db_session.refresh(chat)
    assert chat.classificacao_demanda_pendente is False

    meus = client.get("/v1/whatsapp/chats/meus", headers=auth_headers["a1"]).json()
    assert not any(c["id"] == chat.id for c in meus)
