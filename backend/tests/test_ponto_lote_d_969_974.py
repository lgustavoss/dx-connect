"""Lote D: solicitação HE (#969) + teto mensal (#974)."""

from datetime import date


def _patch_jornada_semanal(client, headers, atendente_id: int, *, fim="23:59"):
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


def test_colaborador_solicita_he_com_janela(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    a1 = seed_base["a1"]
    r = client.post(
        "/v1/ponto/hora-extra",
        headers=user,
        json={"motivo": "Pico", "modo": "duracao", "duracao_minutos": 45},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["estado"] == "pendente"
    assert body["modo"] == "duracao"
    assert "45 min" in (body.get("motivo") or "")
    pend = client.get("/v1/ponto/hora-extra?estado=pendente", headers=admin)
    assert pend.status_code == 200
    assert any(x["id"] == body["id"] for x in pend.json())
    st = client.get("/v1/ponto/hora-extra/me/status", headers=user)
    assert st.status_code == 200
    assert st.json()["pedido_pendente"]["id"] == body["id"]
    # Admin aprova usando janela do pedido
    dec = client.post(
        f"/v1/ponto/hora-extra/{body['id']}/decidir",
        headers=admin,
        json={"aprovar": True},
    )
    assert dec.status_code == 200, dec.text
    assert dec.json()["estado"] == "aprovada"
    assert dec.json()["modo"] == "duracao"
    st2 = client.get("/v1/ponto/hora-extra/me/status", headers=user)
    assert st2.json()["he_ativa"] is not None
    _ = a1  # seed usado via auth


def test_he_rejeitada_feedback(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    sol = client.post(
        "/v1/ponto/hora-extra",
        headers=user,
        json={"motivo": "Preciso", "modo": "resto_do_dia"},
    )
    assert sol.status_code == 201, sol.text
    he_id = sol.json()["id"]
    dec = client.post(
        f"/v1/ponto/hora-extra/{he_id}/decidir",
        headers=admin,
        json={"aprovar": False, "decisao_motivo": "Sem necessidade hoje"},
    )
    assert dec.status_code == 200
    st = client.get("/v1/ponto/hora-extra/me/status", headers=user)
    assert st.status_code == 200
    rej = st.json()["ultimo_rejeitado"]
    assert rej is not None
    assert "Sem necessidade" in (rej.get("decisao_motivo") or "")


def test_teto_mensal_bloqueia_concessao(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    a1 = seed_base["a1"]
    assert client.patch(
        f"/v1/atendentes/{a1.id}",
        headers=admin,
        json={"he_teto_mensal_minutos": 60},
    ).status_code == 200
    r1 = client.post(
        "/v1/ponto/hora-extra/conceder",
        headers=admin,
        json={"atendente_id": a1.id, "modo": "duracao", "duracao_minutos": 60},
    )
    assert r1.status_code == 201, r1.text
    r2 = client.post(
        "/v1/ponto/hora-extra/conceder",
        headers=admin,
        json={"atendente_id": a1.id, "modo": "duracao", "duracao_minutos": 30},
    )
    assert r2.status_code == 400, r2.text
    assert "mensal" in r2.json()["detail"].lower()


def test_teto_mensal_global_settings_e_digest(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    a1 = seed_base["a1"]
    st = client.patch(
        "/v1/ponto/settings",
        headers=admin,
        json={"he_teto_mensal_minutos": 45},
    )
    assert st.status_code == 200, st.text
    assert st.json()["he_teto_mensal_minutos"] == 45
    assert client.post(
        "/v1/ponto/hora-extra/conceder",
        headers=admin,
        json={"atendente_id": a1.id, "modo": "duracao", "duracao_minutos": 45},
    ).status_code == 201
    # Segunda concessão estoura
    assert (
        client.post(
            "/v1/ponto/hora-extra/conceder",
            headers=admin,
            json={"atendente_id": a1.id, "modo": "duracao", "duracao_minutos": 30},
        ).status_code
        == 400
    )
    dig = client.get("/v1/ponto/digest", headers=admin)
    assert dig.status_code == 200
    assert "he_acima_teto_mensal" in dig.json()
    # Consumido == teto ainda não conta como "acima" (> teto)
    assert dig.json()["he_acima_teto_mensal"] >= 0


def test_solicitar_bloqueado_quando_teto_mensal_cheio(client, seed_base, auth_headers, db_session):
    from app.models.ponto_hora_extra import PontoHoraExtra

    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    a1 = seed_base["a1"]
    assert client.patch(
        f"/v1/atendentes/{a1.id}",
        headers=admin,
        json={"he_teto_mensal_minutos": 30},
    ).status_code == 200
    assert client.post(
        "/v1/ponto/hora-extra/conceder",
        headers=admin,
        json={"atendente_id": a1.id, "modo": "duracao", "duracao_minutos": 30},
    ).status_code == 201
    # Expira a HE ativa para isolar o bloqueio de teto mensal
    row = (
        db_session.query(PontoHoraExtra)
        .filter(PontoHoraExtra.atendente_id == a1.id, PontoHoraExtra.estado == "aprovada")
        .order_by(PontoHoraExtra.id.desc())
        .first()
    )
    assert row is not None
    row.estado = "expirada"
    db_session.commit()
    r = client.post(
        "/v1/ponto/hora-extra",
        headers=user,
        json={"motivo": "Mais", "modo": "duracao", "duracao_minutos": 30},
    )
    assert r.status_code == 400
    assert "mensal" in r.json()["detail"].lower()


def test_me_status_campos_mensais(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    a1 = seed_base["a1"]
    assert client.patch(
        f"/v1/atendentes/{a1.id}",
        headers=admin,
        json={"he_teto_mensal_minutos": 120},
    ).status_code == 200
    assert _patch_jornada_semanal(client, admin, a1.id, fim="18:00").status_code == 200
    st = client.get("/v1/ponto/hora-extra/me/status", headers=user)
    assert st.status_code == 200
    body = st.json()
    assert body["he_teto_mensal_minutos"] == 120
    assert body["he_consumido_mensal_minutos"] >= 0
