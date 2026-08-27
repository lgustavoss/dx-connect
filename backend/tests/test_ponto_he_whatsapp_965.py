"""Bloqueio de pegar WhatsApp após jornada + HE admin (#965)."""

from datetime import date, datetime, timedelta

from app.services.escala import PONTO_TZ


def _patch_jornada_semanal(client, headers, atendente_id: int, *, fim="12:00"):
    """Grade só hoje com saída no passado (fim cedo) para forçar fora da jornada."""
    keys = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]
    hoje_key = keys[date.today().weekday()]
    hs = {k: {"ativo": False, "inicio": "08:00", "fim": "18:00"} for k in keys}
    hs[hoje_key] = {"ativo": True, "inicio": "06:00", "fim": fim}
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


def _criar_chat_fila(db_session, seed_base, *, wa_suffix: str):
    from app.models.whatsapp_chat import WhatsappChat

    chat = WhatsappChat(
        wa_id=f"551199999{wa_suffix}",
        protocolo=f"WPP-TEST-965-{wa_suffix}",
        estado="aguardando_atendente",
        setor_id=seed_base["setor1"].id,
    )
    db_session.add(chat)
    db_session.commit()
    db_session.refresh(chat)
    return chat.id


def test_assumir_bloqueado_apos_jornada(client, seed_base, auth_headers, db_session):
    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    a1 = seed_base["a1"]
    fim = (datetime.now(PONTO_TZ) - timedelta(hours=1)).strftime("%H:%M")
    r_patch = _patch_jornada_semanal(client, admin, a1.id, fim=fim)
    assert r_patch.status_code == 200, r_patch.text
    chat_id = _criar_chat_fila(db_session, seed_base, wa_suffix="650")
    r = client.post(f"/v1/whatsapp/chats/{chat_id}/assumir", headers=user)
    assert r.status_code == 403, r.text
    assert "jornada" in r.json()["detail"].lower()
    pend = client.get("/v1/ponto/hora-extra?estado=pendente", headers=admin)
    assert pend.status_code == 200
    assert any(x["atendente_id"] == a1.id for x in pend.json())


def test_assumir_ok_com_he(client, seed_base, auth_headers, db_session):
    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    a1 = seed_base["a1"]
    fim = (datetime.now(PONTO_TZ) - timedelta(hours=1)).strftime("%H:%M")
    assert _patch_jornada_semanal(client, admin, a1.id, fim=fim).status_code == 200
    chat_id = _criar_chat_fila(db_session, seed_base, wa_suffix="651")
    assert client.post(f"/v1/whatsapp/chats/{chat_id}/assumir", headers=user).status_code == 403
    pend = client.get("/v1/ponto/hora-extra?estado=pendente", headers=admin).json()
    he_id = next(x["id"] for x in pend if x["atendente_id"] == a1.id)
    dec = client.post(
        f"/v1/ponto/hora-extra/{he_id}/decidir",
        headers=admin,
        json={"aprovar": True, "modo": "resto_do_dia"},
    )
    assert dec.status_code == 200, dec.text
    assert dec.json()["estado"] == "aprovada"
    chat_id2 = _criar_chat_fila(db_session, seed_base, wa_suffix="652")
    r = client.post(f"/v1/whatsapp/chats/{chat_id2}/assumir", headers=user)
    assert r.status_code == 200, r.text


def test_assumir_ok_modo_nenhum(client, seed_base, auth_headers, db_session):
    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    a1 = seed_base["a1"]
    assert client.patch(
        f"/v1/atendentes/{a1.id}",
        headers=admin,
        json={"modo_jornada": "nenhum", "usa_escala": False},
    ).status_code == 200
    chat_id = _criar_chat_fila(db_session, seed_base, wa_suffix="653")
    r = client.post(f"/v1/whatsapp/chats/{chat_id}/assumir", headers=user)
    assert r.status_code == 200, r.text


def test_he_rejeitada(client, seed_base, auth_headers, db_session):
    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    a1 = seed_base["a1"]
    fim = (datetime.now(PONTO_TZ) - timedelta(hours=2)).strftime("%H:%M")
    assert _patch_jornada_semanal(client, admin, a1.id, fim=fim).status_code == 200
    sol = client.post(
        "/v1/ponto/hora-extra",
        headers=user,
        json={"motivo": "Pico de demanda"},
    )
    assert sol.status_code == 201, sol.text
    he_id = sol.json()["id"]
    dec = client.post(
        f"/v1/ponto/hora-extra/{he_id}/decidir",
        headers=admin,
        json={"aprovar": False, "decisao_motivo": "Sem necessidade"},
    )
    assert dec.status_code == 200
    assert dec.json()["estado"] == "rejeitada"
    st = client.get("/v1/ponto/hora-extra/me/status", headers=user)
    assert st.status_code == 200
    assert st.json()["pode_pegar_whatsapp"] is False
