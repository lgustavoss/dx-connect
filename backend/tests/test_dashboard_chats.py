"""Testes do dashboard chats (#284 / D-03)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models import Ticket
from app.models.whatsapp_chat import WhatsappChat, WhatsappChatTicket, WhatsappMensagem
from app.services.dashboard_chats import CACHE_TTL_SECONDS, clear_dashboard_chats_cache


@pytest.fixture(autouse=True)
def _limpar_cache_dashboard_chats():
    clear_dashboard_chats_cache()
    yield
    clear_dashboard_chats_cache()


def _criar_chat(
    db_session,
    seed_base,
    *,
    setor_id=None,
    estado="encerrado",
    created_at=None,
    atendimento_inicio_at=None,
    encerramento_at=None,
    nota=None,
):
    agora = datetime.now(timezone.utc)
    suf = datetime.now().timestamp()
    c = WhatsappChat(
        protocolo=f"WD{suf}",
        wa_id=f"5511999{suf}",
        estado=estado,
        setor_id=setor_id or seed_base["setor1"].id,
        atendente_id=seed_base["admin"].id,
        created_at=created_at or agora - timedelta(hours=3),
        atendimento_inicio_at=atendimento_inicio_at or agora - timedelta(hours=2),
        encerramento_at=encerramento_at or (agora if estado == "encerrado" else None),
        avaliacao_nota=nota,
        avaliacao_respondida_at=agora if nota is not None else None,
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


def test_dashboard_chats_volume_e_tempos(client, seed_base, auth_headers, db_session):
    ontem = datetime.now(timezone.utc) - timedelta(days=1)
    _criar_chat(
        db_session,
        seed_base,
        created_at=ontem,
        atendimento_inicio_at=ontem + timedelta(minutes=10),
        encerramento_at=ontem + timedelta(hours=1),
    )

    r = client.get("/v1/dashboard/chats", headers=auth_headers["admin"])
    assert r.status_code == 200
    body = r.json()
    assert body["cache_ttl_segundos"] == CACHE_TTL_SECONDS
    assert sum(d["abertos"] for d in body["volume_por_dia"]) >= 1
    assert body["tempo_espera_medio_horas"] is not None
    assert body["tempo_atendimento_medio_horas"] is not None
    assert body["snapshot"]["chats_aguardando"] >= 0


def test_dashboard_chats_atendente_escopo_setor(client, seed_base, auth_headers, db_session):
    _criar_chat(db_session, seed_base, setor_id=seed_base["setor1"].id, estado="aguardando_atendente")
    _criar_chat(db_session, seed_base, setor_id=seed_base["setor2"].id, estado="aguardando_atendente")

    r = client.get("/v1/dashboard/chats", headers=auth_headers["a1"])
    assert r.status_code == 200
    assert sum(x["total"] for x in r.json()["por_estado_atual"]) == 1


def test_dashboard_chats_encerramento_e_vinculo_ticket(client, seed_base, auth_headers, db_session):
    ontem = datetime.now(timezone.utc) - timedelta(days=1)
    chat = _criar_chat(
        db_session,
        seed_base,
        created_at=ontem,
        atendimento_inicio_at=ontem + timedelta(minutes=5),
        encerramento_at=ontem + timedelta(hours=1),
        nota=5,
    )
    db_session.add(
        WhatsappMensagem(
            chat_id=chat.id,
            direcao="outbound",
            corpo="Encerrado por inatividade",
            evento_sistema="auto_encerrado_inatividade",
        )
    )
    ticket = Ticket(
        tenant_id=1,
        protocolo=f"TV-{datetime.now().timestamp()}",
        empresa_id=seed_base["empresa"].id,
        setor_id=seed_base["setor1"].id,
        status_id=seed_base["status"].id,
        assunto="Vinculo chat",
    )
    db_session.add(ticket)
    db_session.commit()
    db_session.add(WhatsappChatTicket(chat_id=chat.id, ticket_id=ticket.id, atendente_id=seed_base["admin"].id))
    db_session.commit()

    r = client.get("/v1/dashboard/chats", headers=auth_headers["admin"])
    assert r.status_code == 200
    body = r.json()
    assert body["avaliacoes"]["total_avaliacoes"] >= 1
    assert body["pct_com_ticket_vinculado"] == 100.0
    inat = next(x for x in body["encerramentos"] if x["tipo"] == "inatividade")
    assert inat["total"] >= 1
    assert len(body["por_atendente"]) >= 1
