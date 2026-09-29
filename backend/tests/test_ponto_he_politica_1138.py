"""Política banco vs pagamento de HE (#1138)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.models.atendente import Atendente
from app.services import ponto as ponto_svc
from app.services.ponto_settings import get_or_create_settings

HS_SEG_SEX = {
    "seg": {"ativo": True, "inicio": "08:00", "fim": "16:00"},
    "ter": {"ativo": True, "inicio": "08:00", "fim": "16:00"},
    "qua": {"ativo": True, "inicio": "08:00", "fim": "16:00"},
    "qui": {"ativo": True, "inicio": "08:00", "fim": "16:00"},
    "sex": {"ativo": True, "inicio": "08:00", "fim": "16:00"},
    "sab": {"ativo": False, "inicio": "08:00", "fim": "12:00"},
    "dom": {"ativo": False, "inicio": "08:00", "fim": "12:00"},
}

# Segunda-feira 2026-08-03
DIA = date(2026, 8, 3)


def _configurar_jornada(client, auth_headers, a1: Atendente) -> None:
    r = client.patch(
        f"/v1/atendentes/{a1.id}",
        headers=auth_headers["admin"],
        json={
            "modo_jornada": "semanal",
            "horario_semana": HS_SEG_SEX,
            "tolerancia_atraso_minutos": 15,
        },
    )
    assert r.status_code == 200, r.text


def _bater_dia(client, auth_headers, a1: Atendente, horas: float) -> None:
    inicio = datetime(2026, 8, 3, 11, 0, tzinfo=timezone.utc)  # 08:00 BRT
    fim = inicio + timedelta(hours=horas)
    r1 = client.post(
        "/v1/ponto/batidas",
        headers=auth_headers["admin"],
        json={
            "atendente_id": a1.id,
            "tipo": "entrada",
            "registrado_em": inicio.isoformat(),
            "motivo": "teste he política",
        },
    )
    assert r1.status_code == 201, r1.text
    r2 = client.post(
        "/v1/ponto/batidas",
        headers=auth_headers["admin"],
        json={
            "atendente_id": a1.id,
            "tipo": "saida",
            "registrado_em": fim.isoformat(),
            "motivo": "teste he política",
        },
    )
    assert r2.status_code == 201, r2.text


def test_he_politica_misto_2h_banco_resto_pago(client, seed_base, auth_headers, db_session):
    a1: Atendente = seed_base["a1"]
    _configurar_jornada(client, auth_headers, a1)
    st = client.patch(
        "/v1/ponto/settings",
        headers=auth_headers["admin"],
        json={
            "banco_horas_ativo": True,
            "he_destino_excedente": "misto",
            "he_banco_primeiros_minutos": 120,
        },
    )
    assert st.status_code == 200, st.text
    assert st.json()["he_destino_excedente"] == "misto"
    assert st.json()["he_banco_primeiros_minutos"] == 120

    # Jornada 8h; trabalha 11h → extra 3h → 2h banco + 1h pago
    _bater_dia(client, auth_headers, a1, horas=11)

    bh = client.get(
        "/v1/ponto/me/banco-horas",
        headers=auth_headers["a1"],
        params={"desde": DIA.isoformat(), "ate": DIA.isoformat()},
    )
    assert bh.status_code == 200, bh.text
    body = bh.json()
    assert body["segundos_esperados"] == 8 * 3600
    assert body["segundos_realizados"] == 11 * 3600
    assert body["saldo_segundos"] == 2 * 3600
    assert body["segundos_he_pagos"] == 1 * 3600


def test_he_politica_pagamento_e_banco_off(client, seed_base, auth_headers, db_session):
    a1: Atendente = seed_base["a1"]
    _configurar_jornada(client, auth_headers, a1)

    client.patch(
        "/v1/ponto/settings",
        headers=auth_headers["admin"],
        json={
            "banco_horas_ativo": True,
            "he_destino_excedente": "pagamento",
            "he_banco_primeiros_minutos": 120,
        },
    )
    _bater_dia(client, auth_headers, a1, horas=10)
    bh = client.get(
        "/v1/ponto/me/banco-horas",
        headers=auth_headers["a1"],
        params={"desde": DIA.isoformat(), "ate": DIA.isoformat()},
    )
    body = bh.json()
    assert body["saldo_segundos"] == 0
    assert body["segundos_he_pagos"] == 2 * 3600

    # Limpa batidas do dia via política banco off + destino banco
    settings = get_or_create_settings(db_session, a1.tenant_id)
    settings.banco_horas_ativo = False
    settings.he_destino_excedente = "banco"
    db_session.commit()

    bh2 = ponto_svc.banco_horas(db_session, a1, desde=DIA, ate=DIA)
    assert bh2.saldo_segundos == 0
    assert bh2.segundos_he_pagos == 0


def test_he_politica_tudo_banco(client, seed_base, auth_headers, db_session):
    a1: Atendente = seed_base["a1"]
    _configurar_jornada(client, auth_headers, a1)
    client.patch(
        "/v1/ponto/settings",
        headers=auth_headers["admin"],
        json={
            "banco_horas_ativo": True,
            "he_destino_excedente": "banco",
        },
    )
    _bater_dia(client, auth_headers, a1, horas=9)
    bh = client.get(
        "/v1/ponto/me/banco-horas",
        headers=auth_headers["a1"],
        params={"desde": DIA.isoformat(), "ate": DIA.isoformat()},
    )
    body = bh.json()
    assert body["saldo_segundos"] == 1 * 3600
    assert body.get("segundos_he_pagos", 0) == 0
