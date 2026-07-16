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


def _chat_em_atendimento(db_session, *, wa_id: str = "5511999887766") -> WhatsappChat:
    chat = WhatsappChat(
        protocolo="WPP-TEST-1",
        wa_id=wa_id,
        cliente_nome="Cliente Teste",
        estado="em_atendimento",
        atendente_id=1,
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


def test_worker_nao_age_quando_cliente_respondeu_por_ultimo(client, seed_base, auth_headers, db_session, monkeypatch):
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


def test_worker_aviso_mesmo_com_atendente_enviando_varias_vezes(
    client, seed_base, auth_headers, db_session, monkeypatch
):
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
    assert n == 1


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
