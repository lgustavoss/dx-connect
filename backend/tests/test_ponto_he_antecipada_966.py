"""HE antecipada + teto (#966)."""

from datetime import datetime, timedelta, timezone

from app.services.escala import PONTO_TZ


def _janela_encerrada(*, agora: datetime | None = None, fim: str | None = None) -> tuple[str, str]:
    """Retorna (inicio, fim) com início < fim e fim já no passado (TZ do ponto)."""
    import pytest

    agora = agora or datetime.now(PONTO_TZ)
    if fim is not None:
        fh, fm = (int(x) for x in fim.split(":"))
        fim_dt = agora.replace(hour=fh, minute=fm, second=0, microsecond=0)
        if fim_dt < agora:
            inicio_dt = fim_dt - timedelta(hours=2)
            if inicio_dt.date() == fim_dt.date():
                inicio = inicio_dt.strftime("%H:%M")
                if inicio < fim:
                    return inicio, fim
            elif fim > "00:00":
                return "00:00", fim

    fim_dt = agora - timedelta(minutes=30)
    inicio_dt = agora - timedelta(hours=2)
    if fim_dt.date() < agora.date() or inicio_dt.date() < agora.date():
        if agora.hour == 0 and agora.minute < 5:
            pytest.skip("janela de teste instável nos primeiros minutos após meia-noite")
        inicio = "00:00"
        fim_s = (agora - timedelta(minutes=2)).strftime("%H:%M")
        if inicio >= fim_s:
            pytest.skip("janela de teste instável nos primeiros minutos após meia-noite")
        return inicio, fim_s
    return inicio_dt.strftime("%H:%M"), fim_dt.strftime("%H:%M")


def _patch_jornada_semanal(client, headers, atendente_id: int, *, fim: str | None = None):
    keys = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]
    agora = datetime.now(PONTO_TZ)
    hoje_key = keys[agora.weekday()]
    inicio, fim_ok = _janela_encerrada(agora=agora, fim=fim)
    hs = {k: {"ativo": False, "inicio": "08:00", "fim": "18:00"} for k in keys}
    hs[hoje_key] = {"ativo": True, "inicio": inicio, "fim": fim_ok}
    return client.patch(
        f"/v1/atendentes/{atendente_id}",
        headers=headers,
        json={
            "modo_jornada": "semanal",
            "usa_escala": True,
            "horario_semana": hs,
            "tolerancia_atraso_minutos": 0,
        },
    )


def test_conceder_he_antecipada_durante_jornada(client, seed_base, auth_headers, monkeypatch):
    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    a1 = seed_base["a1"]
    agora = datetime(2026, 6, 17, 14, 0, tzinfo=PONTO_TZ)
    monkeypatch.setattr(
        "app.services.ponto._agora_utc",
        lambda: agora.astimezone(timezone.utc),
    )
    # Durante a jornada: início < agora < fim (não usa janela “encerrada”).
    keys = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]
    hoje_key = keys[agora.weekday()]
    hs = {k: {"ativo": False, "inicio": "08:00", "fim": "18:00"} for k in keys}
    hs[hoje_key] = {"ativo": True, "inicio": "06:00", "fim": "18:00"}
    assert (
        client.patch(
            f"/v1/atendentes/{a1.id}",
            headers=admin,
            json={
                "modo_jornada": "semanal",
                "usa_escala": True,
                "horario_semana": hs,
                "tolerancia_atraso_minutos": 0,
            },
        ).status_code
        == 200
    )
    r = client.post(
        "/v1/ponto/hora-extra/conceder",
        headers=admin,
        json={"atendente_id": a1.id, "modo": "duracao", "duracao_minutos": 90, "motivo": "Pico"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["estado"] == "aprovada"
    assert body["origem"] == "admin"
    assert body["modo"] == "duracao"
    st = client.get("/v1/ponto/hora-extra/me/status", headers=user)
    assert st.status_code == 200
    assert st.json()["he_ativa"] is not None
    assert st.json()["he_restante_minutos"] is not None
    assert st.json()["he_restante_minutos"] <= 90


def test_teto_limita_concessao(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    a1 = seed_base["a1"]
    assert client.patch(
        f"/v1/atendentes/{a1.id}",
        headers=admin,
        json={"he_teto_minutos": 60},
    ).status_code == 200
    # Pedido resto do dia seria até 23:59 — teto de 60 min corta
    r = client.post(
        "/v1/ponto/hora-extra/conceder",
        headers=admin,
        json={"atendente_id": a1.id, "modo": "resto_do_dia"},
    )
    assert r.status_code == 201, r.text
    ate = datetime.fromisoformat(r.json()["ate_em"].replace("Z", "+00:00"))
    agora = datetime.now(PONTO_TZ)
    delta_min = (ate.astimezone(PONTO_TZ) - agora).total_seconds() / 60
    assert delta_min <= 61


def test_teto_bloqueia_duracao_maior(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    a1 = seed_base["a1"]
    assert client.patch(
        f"/v1/atendentes/{a1.id}",
        headers=admin,
        json={"he_teto_minutos": 30},
    ).status_code == 200
    # 30 min teto + modo duracao 30 = ok
    r_ok = client.post(
        "/v1/ponto/hora-extra/conceder",
        headers=admin,
        json={"atendente_id": a1.id, "modo": "duracao", "duracao_minutos": 30},
    )
    assert r_ok.status_code == 201, r_ok.text
    # Nova concessão 120 com teto 30: ainda deve criar mas cortada a 30
    r2 = client.post(
        "/v1/ponto/hora-extra/conceder",
        headers=admin,
        json={"atendente_id": a1.id, "modo": "duracao", "duracao_minutos": 120},
    )
    assert r2.status_code == 201, r2.text
    ate = datetime.fromisoformat(r2.json()["ate_em"].replace("Z", "+00:00"))
    agora = datetime.now(PONTO_TZ)
    assert (ate.astimezone(PONTO_TZ) - agora).total_seconds() / 60 <= 31


def test_he_ativa_libera_apos_jornada(client, seed_base, auth_headers, db_session):
    from app.models.whatsapp_chat import WhatsappChat

    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    a1 = seed_base["a1"]
    # Concede antes
    assert client.post(
        "/v1/ponto/hora-extra/conceder",
        headers=admin,
        json={"atendente_id": a1.id, "modo": "duracao", "duracao_minutos": 120},
    ).status_code == 201
    # Força fim da jornada no passado
    assert _patch_jornada_semanal(client, admin, a1.id).status_code == 200
    chat = WhatsappChat(
        wa_id="5511999999660",
        protocolo="WPP-TEST-966",
        estado="aguardando_atendente",
        setor_id=seed_base["setor1"].id,
    )
    db_session.add(chat)
    db_session.commit()
    db_session.refresh(chat)
    r = client.post(f"/v1/whatsapp/chats/{chat.id}/assumir", headers=user)
    assert r.status_code == 200, r.text
