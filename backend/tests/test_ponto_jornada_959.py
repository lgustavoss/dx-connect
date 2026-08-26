"""Ponto jornada semanal, janela de entrada e fecho por esquecimento (#959 Lote A)."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException

from app.models.ponto_batida import PontoBatida
from app.services import escala as escala_svc
from app.services import ponto as ponto_svc
from app.services.ponto import _atrasado_entrada
from app.services.ponto_settings import get_or_create_settings, processar_fecho_automatico

TZ = ZoneInfo("America/Sao_Paulo")

HS_SEG_SEX = {
    "seg": {"ativo": True, "inicio": "08:00", "fim": "18:00"},
    "ter": {"ativo": True, "inicio": "08:00", "fim": "18:00"},
    "qua": {"ativo": True, "inicio": "08:00", "fim": "18:00"},
    "qui": {"ativo": True, "inicio": "08:00", "fim": "18:00"},
    "sex": {"ativo": True, "inicio": "08:00", "fim": "17:00"},
    "sab": {"ativo": False, "inicio": "08:00", "fim": "12:00"},
    "dom": {"ativo": False, "inicio": "08:00", "fim": "12:00"},
}


def test_jornada_semanal_seg_sex_e_modo_nenhum(client, seed_base, auth_headers, db_session):
    a1 = seed_base["a1"]
    r = client.patch(
        f"/v1/atendentes/{a1.id}",
        headers=auth_headers["admin"],
        json={"modo_jornada": "semanal", "horario_semana": HS_SEG_SEX, "tolerancia_atraso_minutos": 15},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["modo_jornada"] == "semanal"
    assert body["usa_escala"] is True
    assert body["horario_semana"]["sex"]["fim"] == "17:00"

    db_session.expire_all()
    db_session.refresh(a1)
    assert escala_svc.eh_dia_de_trabalho(a1, date(2026, 8, 26)) is True  # qua
    assert escala_svc.eh_dia_de_trabalho(a1, date(2026, 8, 29)) is False  # sáb
    assert escala_svc.eh_dia_de_trabalho(a1, date(2026, 8, 30)) is False  # dom

    r2 = client.patch(
        f"/v1/atendentes/{a1.id}",
        headers=auth_headers["admin"],
        json={"modo_jornada": "nenhum"},
    )
    assert r2.status_code == 200
    db_session.expire_all()
    db_session.refresh(a1)
    assert escala_svc.escala_configurada(a1) is False
    cal = client.get(
        "/v1/ponto/me/calendario",
        headers=auth_headers["a1"],
        params={"ano": 2026, "mes": 8},
    )
    assert cal.status_code == 200
    dia = next(d for d in cal.json()["dias"] if d["data"] == "2026-08-26")
    assert dia["status"] == "livre"


def test_entrada_janela_e_atraso_na_tolerancia(client, seed_base, auth_headers, db_session):
    a1 = seed_base["a1"]
    a1.modo_jornada = "semanal"
    a1.usa_escala = True
    a1.tolerancia_atraso_minutos = 15
    a1.horario_semana_json = json.dumps(HS_SEG_SEX, ensure_ascii=False)
    db_session.flush()

    early = datetime(2026, 8, 26, 7, 0, tzinfo=TZ)
    with pytest.raises(HTTPException) as ei:
        escala_svc.validar_janela_entrada(a1, early)
    assert ei.value.status_code == 400

    escala_svc.validar_janela_entrada(a1, datetime(2026, 8, 26, 7, 50, tzinfo=TZ))

    bat_ok = PontoBatida(
        tenant_id=a1.tenant_id,
        atendente_id=a1.id,
        tipo="entrada",
        registrado_em=datetime(2026, 8, 26, 8, 10, tzinfo=TZ),
        origem="admin",
        anulada=False,
    )
    assert _atrasado_entrada(a1, bat_ok) is False

    bat_late = PontoBatida(
        tenant_id=a1.tenant_id,
        atendente_id=a1.id,
        tipo="entrada",
        registrado_em=datetime(2026, 8, 26, 8, 20, tzinfo=TZ),
        origem="admin",
        anulada=False,
    )
    assert _atrasado_entrada(a1, bat_late) is True


def test_fecho_por_saida_prevista(client, seed_base, auth_headers, db_session):
    a1 = seed_base["a1"]
    agora_local = datetime.now(TZ)
    fim_dt = agora_local - timedelta(minutes=45)
    ini_dt = agora_local - timedelta(hours=8)
    ini = ini_dt.strftime("%H:%M")
    fim = fim_dt.strftime("%H:%M")
    if ini >= fim:
        ini = "00:00"
        fim = "00:15"
        ini_dt = agora_local.replace(hour=0, minute=0, second=0, microsecond=0)
        # se ainda estamos antes de 00:15, força fim no passado relativo
        if agora_local.hour == 0 and agora_local.minute < 15:
            fim = "00:01"

    weekday_keys = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]
    k = weekday_keys[agora_local.weekday()]
    hs = {d: {"ativo": False, "inicio": "08:00", "fim": "18:00"} for d in weekday_keys}
    hs[k] = {"ativo": True, "inicio": ini, "fim": fim}

    a1.modo_jornada = "semanal"
    a1.usa_escala = True
    a1.tolerancia_atraso_minutos = 0
    a1.horario_semana_json = json.dumps(hs, ensure_ascii=False)

    st = get_or_create_settings(db_session, a1.tenant_id)
    st.fecho_automatico_ativo = True
    st.fecho_apos_horas = 48
    st.fecho_margem_pos_saida_minutos = 0
    db_session.flush()

    ponto_svc.bater(
        db_session,
        a1,
        "entrada",
        origem="admin",
        registrado_em=ini_dt,
        commit=False,
    )
    db_session.flush()

    n = processar_fecho_automatico(db_session, limit=10)
    assert n >= 1
    db_session.commit()
    me = client.get("/v1/ponto/me", headers=auth_headers["a1"])
    assert me.json()["em_jornada"] is False
