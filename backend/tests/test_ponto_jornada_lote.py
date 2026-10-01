"""Jornada com intervalo, duas jornadas abertas e exclusão de solicitação (#1146–#1151)."""

from __future__ import annotations

from datetime import date

HS_8_18 = {
    "seg": {"ativo": True, "inicio": "08:00", "fim": "18:00"},
    "ter": {"ativo": True, "inicio": "08:00", "fim": "18:00"},
    "qua": {"ativo": True, "inicio": "08:00", "fim": "18:00"},
    "qui": {"ativo": True, "inicio": "08:00", "fim": "18:00"},
    "sex": {"ativo": True, "inicio": "08:00", "fim": "18:00"},
    "sab": {"ativo": False, "inicio": "08:00", "fim": "12:00"},
    "dom": {"ativo": False, "inicio": "08:00", "fim": "12:00"},
}

# Segunda 2026-08-03. 11:00 UTC = 08:00 em America/Sao_Paulo.
DIA = date(2026, 8, 3)


def _jornada(client, auth_headers, a1, hs: dict) -> None:
    r = client.patch(
        f"/v1/atendentes/{a1.id}",
        headers=auth_headers["admin"],
        json={"modo_jornada": "semanal", "horario_semana": hs, "tolerancia_atraso_minutos": 0},
    )
    assert r.status_code == 200, r.text


def _bater(client, auth_headers, a1, quando: str, tipo: str):
    return client.post(
        "/v1/ponto/batidas",
        headers=auth_headers["admin"],
        json={
            "atendente_id": a1.id,
            "tipo": tipo,
            "registrado_em": quando,
            "motivo": "ajuste de teste",
        },
    )


def _banco(client, auth_headers):
    r = client.get(
        "/v1/ponto/me/banco-horas",
        headers=auth_headers["a1"],
        params={"desde": DIA.isoformat(), "ate": DIA.isoformat()},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_escala_8_18_sem_intervalo_preve_10h_e_soma_os_dois_periodos(client, seed_base, auth_headers):
    a1 = seed_base["a1"]
    _jornada(client, auth_headers, a1, HS_8_18)
    client.patch(
        "/v1/ponto/settings",
        headers=auth_headers["admin"],
        json={"banco_horas_ativo": True, "he_destino_excedente": "banco"},
    )
    # 08–12 e 13–18 = 9h realizadas; meta sem intervalo continua 10h.
    assert _bater(client, auth_headers, a1, "2026-08-03T11:00:00+00:00", "entrada").status_code == 201
    assert _bater(client, auth_headers, a1, "2026-08-03T15:00:00+00:00", "saida").status_code == 201
    assert _bater(client, auth_headers, a1, "2026-08-03T16:00:00+00:00", "entrada").status_code == 201
    assert _bater(client, auth_headers, a1, "2026-08-03T21:00:00+00:00", "saida").status_code == 201
    body = _banco(client, auth_headers)
    assert body["segundos_esperados"] == 10 * 3600
    assert body["segundos_realizados"] == 9 * 3600


def test_intervalo_de_1h_desconta_da_meta(client, seed_base, auth_headers):
    a1 = seed_base["a1"]
    hs = {k: dict(v) for k, v in HS_8_18.items()}
    for dia in ("seg", "ter", "qua", "qui", "sex"):
        hs[dia]["intervalo_inicio"] = "12:00"
        hs[dia]["intervalo_fim"] = "13:00"
    _jornada(client, auth_headers, a1, hs)
    client.patch(
        "/v1/ponto/settings",
        headers=auth_headers["admin"],
        json={"banco_horas_ativo": True, "he_destino_excedente": "banco"},
    )
    assert _bater(client, auth_headers, a1, "2026-08-03T11:00:00+00:00", "entrada").status_code == 201
    assert _bater(client, auth_headers, a1, "2026-08-03T15:00:00+00:00", "saida").status_code == 201
    assert _bater(client, auth_headers, a1, "2026-08-03T16:00:00+00:00", "entrada").status_code == 201
    assert _bater(client, auth_headers, a1, "2026-08-03T21:00:00+00:00", "saida").status_code == 201
    body = _banco(client, auth_headers)
    assert body["segundos_esperados"] == 9 * 3600
    assert body["segundos_realizados"] == 9 * 3600
    assert body["saldo_segundos"] == 0


def test_ajuste_recusa_duas_jornadas_abertas(client, seed_base, auth_headers):
    a1 = seed_base["a1"]
    r1 = _bater(client, auth_headers, a1, "2026-08-03T11:00:00+00:00", "entrada")
    assert r1.status_code == 201, r1.text
    r2 = _bater(client, auth_headers, a1, "2026-08-03T16:00:00+00:00", "entrada")
    assert r2.status_code == 400, r2.text
    assert "duas jornadas" in r2.json()["detail"]


def test_volta_do_intervalo_continua_uma_jornada(client, seed_base, auth_headers):
    a1 = seed_base["a1"]
    assert _bater(client, auth_headers, a1, "2026-08-03T11:00:00+00:00", "entrada").status_code == 201
    assert _bater(client, auth_headers, a1, "2026-08-03T15:00:00+00:00", "saida").status_code == 201
    r = _bater(client, auth_headers, a1, "2026-08-03T16:00:00+00:00", "entrada")
    assert r.status_code == 201, r.text


def test_autor_exclui_solicitacao_pendente(client, seed_base, auth_headers):
    user = auth_headers["a1"]
    outro = auth_headers["a2"]
    r = client.post(
        "/v1/ponto/solicitacoes-ajuste",
        headers=user,
        json={
            "tipo": "inclusao",
            "tipo_batida": "entrada",
            "horario_solicitado": "2026-09-22T11:00:00+00:00",
            "motivo": "Esqueci de bater",
            "data_ref": "2026-09-22",
        },
    )
    assert r.status_code == 201, r.text
    sid = r.json()["id"]

    r403 = client.delete(f"/v1/ponto/solicitacoes-ajuste/{sid}", headers=outro)
    assert r403.status_code == 403

    r_ok = client.delete(f"/v1/ponto/solicitacoes-ajuste/{sid}", headers=user)
    assert r_ok.status_code == 200, r_ok.text
    assert r_ok.json()["estado"] == "cancelada"

    r_de_novo = client.delete(f"/v1/ponto/solicitacoes-ajuste/{sid}", headers=user)
    assert r_de_novo.status_code == 400
