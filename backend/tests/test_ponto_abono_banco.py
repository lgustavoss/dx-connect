"""Déficit no banco + abono de falta + alertas sem horário."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.models.atendente import Atendente
from app.services import ponto as ponto_svc

HS_SEG_SEX = {
    "seg": {"ativo": True, "inicio": "08:00", "fim": "16:00"},
    "ter": {"ativo": True, "inicio": "08:00", "fim": "16:00"},
    "qua": {"ativo": True, "inicio": "08:00", "fim": "16:00"},
    "qui": {"ativo": True, "inicio": "08:00", "fim": "16:00"},
    "sex": {"ativo": True, "inicio": "08:00", "fim": "16:00"},
    "sab": {"ativo": False, "inicio": "08:00", "fim": "12:00"},
    "dom": {"ativo": False, "inicio": "08:00", "fim": "12:00"},
}

DIA = date(2026, 8, 3)  # segunda


def _jornada(client, auth_headers, a1: Atendente) -> None:
    r = client.patch(
        f"/v1/atendentes/{a1.id}",
        headers=auth_headers["admin"],
        json={
            "modo_jornada": "semanal",
            "horario_semana": HS_SEG_SEX,
            "tolerancia_atraso_minutos": 10,
        },
    )
    assert r.status_code == 200, r.text


def _bater(client, auth_headers, a1: Atendente, horas: float) -> None:
    inicio = datetime(2026, 8, 3, 11, 0, tzinfo=timezone.utc)
    fim = inicio + timedelta(hours=horas)
    assert (
        client.post(
            "/v1/ponto/batidas",
            headers=auth_headers["admin"],
            json={
                "atendente_id": a1.id,
                "tipo": "entrada",
                "registrado_em": inicio.isoformat(),
                "motivo": "teste",
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/v1/ponto/batidas",
            headers=auth_headers["admin"],
            json={
                "atendente_id": a1.id,
                "tipo": "saida",
                "registrado_em": fim.isoformat(),
                "motivo": "teste",
            },
        ).status_code
        == 201
    )


def test_banco_debita_deficit_do_dia(client, seed_base, auth_headers):
    a1: Atendente = seed_base["a1"]
    _jornada(client, auth_headers, a1)
    client.patch(
        "/v1/ponto/settings",
        headers=auth_headers["admin"],
        json={"banco_horas_ativo": True, "he_destino_excedente": "banco"},
    )
    # Esperado 8h; trabalhou 6h → −2h
    _bater(client, auth_headers, a1, horas=6)
    bh = client.get(
        "/v1/ponto/me/banco-horas",
        headers=auth_headers["a1"],
        params={"desde": DIA.isoformat(), "ate": DIA.isoformat()},
    )
    assert bh.status_code == 200, bh.text
    body = bh.json()
    assert body["segundos_esperados"] == 8 * 3600
    assert body["segundos_realizados"] == 6 * 3600
    assert body["saldo_segundos"] == -2 * 3600
    assert body["segundos_debito_banco"] == 2 * 3600
    assert body["segundos_credito_banco"] == 0


def test_falta_integral_nao_debita_banco(client, seed_base, auth_headers):
    """Dia esperado sem batida = falta: não gera −8h no banco (evita dupla penalidade com desconto salarial)."""
    a1: Atendente = seed_base["a1"]
    _jornada(client, auth_headers, a1)
    client.patch(
        "/v1/ponto/settings",
        headers=auth_headers["admin"],
        json={"banco_horas_ativo": True, "he_destino_excedente": "banco"},
    )
    bh = client.get(
        "/v1/ponto/me/banco-horas",
        headers=auth_headers["a1"],
        params={"desde": DIA.isoformat(), "ate": DIA.isoformat()},
    )
    assert bh.status_code == 200, bh.text
    body = bh.json()
    assert body["segundos_esperados"] == 8 * 3600
    assert body["segundos_realizados"] == 0
    assert body["saldo_segundos"] == 0
    assert body["segundos_debito_banco"] == 0
    assert body["segundos_credito_banco"] == 0


def test_abono_aprovado_nao_e_falta_mas_debita_banco(client, seed_base, auth_headers, db_session):
    """Folga concedida: calendário mostra abono (não falta) e o banco desconta a carga do dia."""
    a1: Atendente = seed_base["a1"]
    _jornada(client, auth_headers, a1)
    db_session.expire_all()
    db_session.refresh(a1)
    bh0 = ponto_svc.banco_horas(db_session, a1, desde=DIA, ate=DIA)
    # Sem batida e sem abono = falta → saldo 0 no banco
    assert bh0.saldo_segundos == 0

    sol = client.post(
        "/v1/ponto/solicitacoes-ajuste",
        headers=auth_headers["a1"],
        json={
            "tipo": "abono",
            "motivo": "Folga acordada com o supervisor — abater banco",
            "data_ref": DIA.isoformat(),
        },
    )
    assert sol.status_code == 201, sol.text
    sid = sol.json()["id"]

    dec = client.post(
        f"/v1/ponto/solicitacoes-ajuste/{sid}/decidir",
        headers=auth_headers["admin"],
        json={"estado": "aprovada", "decisao_motivo": "Acordo ok"},
    )
    assert dec.status_code == 200, dec.text

    db_session.expire_all()
    db_session.refresh(a1)
    bh1 = ponto_svc.banco_horas(db_session, a1, desde=DIA, ate=DIA)
    assert bh1.segundos_esperados == 8 * 3600
    assert bh1.saldo_segundos == -8 * 3600
    assert bh1.segundos_debito_banco == 8 * 3600
    assert bh1.segundos_credito_banco == 0

    cal = client.get(
        "/v1/ponto/me/calendario",
        headers=auth_headers["a1"],
        params={"ano": 2026, "mes": 8},
    )
    dia = next(d for d in cal.json()["dias"] if d["data"] == DIA.isoformat())
    assert dia["ausencia_tipo"] == "abono"
    assert dia["status"] == "abono"
    assert dia["classe_visual"] == "ausencia"
    assert dia["status"] != "falta"


def test_alertas_sem_msgs_de_atraso_ou_saida(client, seed_base, auth_headers, db_session, monkeypatch):
    a1: Atendente = seed_base["a1"]
    _jornada(client, auth_headers, a1)
    # Entrada atrasada e após saída prevista
    inicio = datetime(2026, 8, 3, 14, 0, tzinfo=timezone.utc)  # 11h BRT
    assert (
        client.post(
            "/v1/ponto/batidas",
            headers=auth_headers["admin"],
            json={
                "atendente_id": a1.id,
                "tipo": "entrada",
                "registrado_em": inicio.isoformat(),
                "motivo": "atraso",
            },
        ).status_code
        == 201
    )

    agora = datetime(2026, 8, 3, 21, 0, tzinfo=timezone.utc)  # 18h BRT > 16h fim
    monkeypatch.setattr(ponto_svc, "_agora_utc", lambda: agora)
    monkeypatch.setattr(ponto_svc, "_hoje", lambda: DIA)

    alertas = ponto_svc.alertas_me(db_session, a1)
    joined = " ".join(alertas.mensagens).lower()
    assert "fora da tolerância" not in joined
    assert "horário previsto" not in joined
    assert "janela de" not in joined
    assert alertas.lembrete_entrada_tolerancia is False
    assert alertas.lembrete_saida_tolerancia is False
    assert alertas.sem_entrada_em_dia_escala is False
