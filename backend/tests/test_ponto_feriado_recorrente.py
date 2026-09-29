"""Feriados custom com recorrência anual."""

from __future__ import annotations

from datetime import date

from app.models.atendente import Atendente
from app.services import ponto_settings as settings_svc


def test_feriado_recorrente_vale_nos_anos_seguintes(client, seed_base, auth_headers, db_session):
    a1: Atendente = seed_base["a1"]
    # Cadastro em 2025, marca como recorrente
    r = client.post(
        "/v1/ponto/feriados",
        headers=auth_headers["admin"],
        json={
            "data": "2025-03-15",
            "nome": "Aniversário da rede",
            "recorrente_anual": True,
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["recorrente_anual"] is True

    # Em 2026 o mesmo dia/mês deve contar como feriado
    assert settings_svc.eh_feriado(db_session, a1.tenant_id, date(2026, 3, 15)) is True
    assert settings_svc.eh_feriado(db_session, a1.tenant_id, date(2026, 3, 16)) is False
    # Antes do ano cadastrado não aplica
    assert settings_svc.eh_feriado(db_session, a1.tenant_id, date(2024, 3, 15)) is False

    lista = client.get(
        "/v1/ponto/feriados",
        headers=auth_headers["admin"],
        params={"ano": 2026},
    )
    assert lista.status_code == 200
    body = lista.json()
    assert any(f["data"] == "2026-03-15" and f["recorrente_anual"] for f in body)

    cal = client.get(
        "/v1/ponto/me/calendario",
        headers=auth_headers["a1"],
        params={"ano": 2026, "mes": 3},
    )
    assert cal.status_code == 200
    dia = next(d for d in cal.json()["dias"] if d["data"] == "2026-03-15")
    assert dia["feriado"] is True


def test_feriado_sem_recorrencia_nao_vai_pro_ano_seguinte(client, seed_base, auth_headers, db_session):
    a1: Atendente = seed_base["a1"]
    r = client.post(
        "/v1/ponto/feriados",
        headers=auth_headers["admin"],
        json={"data": "2025-04-10", "nome": "Ponte única", "recorrente_anual": False},
    )
    assert r.status_code == 201, r.text
    assert settings_svc.eh_feriado(db_session, a1.tenant_id, date(2025, 4, 10)) is True
    assert settings_svc.eh_feriado(db_session, a1.tenant_id, date(2026, 4, 10)) is False
