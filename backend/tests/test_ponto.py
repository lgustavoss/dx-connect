"""Controle de ponto (#761+)."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.models.atendente import Atendente
from app.services.escala import eh_dia_de_trabalho, em_periodo_trabalho


def test_ponto_bater_entrada_saida(client, seed_base, auth_headers):
    r = client.post("/v1/ponto/bater", headers=auth_headers["a1"], json={"tipo": "entrada"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tipo"] == "entrada"
    assert body["atendente_id"] == seed_base["a1"].id

    me = client.get("/v1/ponto/me", headers=auth_headers["a1"])
    assert me.status_code == 200
    assert me.json()["em_jornada"] is True
    assert me.json()["entrada_aberta_em"]

    r2 = client.post("/v1/ponto/bater", headers=auth_headers["a1"], json={"tipo": "entrada"})
    assert r2.status_code == 400

    r3 = client.post("/v1/ponto/bater", headers=auth_headers["a1"], json={"tipo": "saida"})
    assert r3.status_code == 200
    assert r3.json()["tipo"] == "saida"

    me2 = client.get("/v1/ponto/me", headers=auth_headers["a1"])
    assert me2.json()["em_jornada"] is False

    r4 = client.post("/v1/ponto/bater", headers=auth_headers["a1"], json={"tipo": "saida"})
    assert r4.status_code == 400


def test_ponto_historico_proprio_e_totais(client, seed_base, auth_headers):
    r1 = client.post("/v1/ponto/bater", headers=auth_headers["a1"], json={"tipo": "entrada"})
    assert r1.status_code == 200, r1.text
    r2 = client.post("/v1/ponto/bater", headers=auth_headers["a1"], json={"tipo": "saida"})
    assert r2.status_code == 200, r2.text

    r = client.get("/v1/ponto/me/batidas", headers=auth_headers["a1"])
    assert r.status_code == 200
    body = r.json()
    # total = nº de intervalos (entrada+saída = 1 intervalo fechado)
    assert body["total"] >= 1
    assert len(body["intervalos"]) >= 1
    assert body["total_segundos_fechados"] >= 0
    assert body["intervalos"][0]["aberto"] is False


def test_ponto_admin_lista_e_403(client, seed_base, auth_headers):
    client.post("/v1/ponto/bater", headers=auth_headers["a1"], json={"tipo": "entrada"})
    client.post("/v1/ponto/bater", headers=auth_headers["a1"], json={"tipo": "saida"})

    r_403 = client.get("/v1/ponto/batidas", headers=auth_headers["a1"])
    assert r_403.status_code == 403

    r = client.get(
        "/v1/ponto/batidas",
        headers=auth_headers["admin"],
        params={"atendente_id": seed_base["a1"].id},
    )
    assert r.status_code == 200
    assert r.json()["total"] >= 2
    assert r.json()["items"][0]["atendente_nome"]


def test_ponto_comercial_bate(client, seed_base, auth_headers):
    r = client.post("/v1/ponto/bater", headers=auth_headers["comercial"], json={"tipo": "entrada"})
    assert r.status_code == 200
    r2 = client.post("/v1/ponto/bater", headers=auth_headers["comercial"], json={"tipo": "saida"})
    assert r2.status_code == 200


def test_ponto_saas_ops_403(client, seed_base, auth_headers):
    r = client.get("/v1/ponto/me", headers=auth_headers["ops"])
    assert r.status_code == 403


def test_escala_12x36_ciclo(db_session, seed_base):
    a1: Atendente = seed_base["a1"]
    a1.usa_escala = True
    a1.escala_horas_trabalho = 12
    a1.escala_horas_folga = 36
    a1.escala_inicio_em = date(2026, 1, 1)
    db_session.add(a1)
    db_session.commit()

    tz = ZoneInfo("America/Sao_Paulo")
    assert em_periodo_trabalho(a1, datetime(2026, 1, 1, 6, 0, tzinfo=tz)) is True
    assert em_periodo_trabalho(a1, datetime(2026, 1, 1, 18, 0, tzinfo=tz)) is False
    assert em_periodo_trabalho(a1, datetime(2026, 1, 2, 12, 0, tzinfo=tz)) is False
    assert em_periodo_trabalho(a1, datetime(2026, 1, 3, 0, 0, tzinfo=tz)) is True

    assert eh_dia_de_trabalho(a1, date(2026, 1, 1)) is True
    assert eh_dia_de_trabalho(a1, date(2026, 1, 2)) is False
    assert eh_dia_de_trabalho(a1, date(2026, 1, 3)) is True


def test_atendente_escala_patch(client, seed_base, auth_headers):
    a1 = seed_base["a1"]
    r = client.patch(
        f"/v1/atendentes/{a1.id}",
        headers=auth_headers["admin"],
        json={
            "usa_escala": True,
            "escala_horas_trabalho": 12,
            "escala_horas_folga": 36,
            "escala_inicio_em": "2026-08-01",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["usa_escala"] is True
    assert body["escala_horas_trabalho"] == 12
    assert body["escala_horas_folga"] == 36
    assert body["escala_inicio_em"] == "2026-08-01"

    r_bad = client.patch(
        f"/v1/atendentes/{a1.id}",
        headers=auth_headers["admin"],
        json={
            "usa_escala": True,
            "escala_horas_trabalho": 12,
            "escala_horas_folga": None,
            "escala_inicio_em": None,
        },
    )
    assert r_bad.status_code == 400

    cal = client.get(
        "/v1/ponto/me/calendario",
        headers=auth_headers["a1"],
        params={"ano": 2026, "mes": 8},
    )
    assert cal.status_code == 200
    assert cal.json()["usa_escala"] is True
    assert cal.json()["escala_rotulo"] == "12×36"
    assert len(cal.json()["dias"]) >= 28


def test_ponto_hoje_admin(client, seed_base, auth_headers):
    # Sem escala ainda pode listar (visão inclui quem tem usa_escala ou todos — ver serviço)
    r = client.get("/v1/ponto/hoje", headers=auth_headers["admin"])
    assert r.status_code == 200
    assert "itens" in r.json()
    r403 = client.get("/v1/ponto/hoje", headers=auth_headers["a1"])
    assert r403.status_code == 403


def test_ponto_pausas_excluem_do_total(client, seed_base, auth_headers):
    h = auth_headers["a1"]
    assert client.post("/v1/ponto/bater", headers=h, json={"tipo": "entrada"}).status_code == 200
    assert client.post("/v1/ponto/bater", headers=h, json={"tipo": "pausa_inicio"}).status_code == 200
    me = client.get("/v1/ponto/me", headers=h).json()
    assert me["em_jornada"] is True
    assert me["em_pausa"] is True
    # #841 — saída com pausa aberta fecha a pausa automaticamente
    r_saida = client.post("/v1/ponto/bater", headers=h, json={"tipo": "saida"})
    assert r_saida.status_code == 200
    assert r_saida.json()["tipo"] == "saida"
    me2 = client.get("/v1/ponto/me", headers=h).json()
    assert me2["em_jornada"] is False
    assert me2["em_pausa"] is False

    hist = client.get("/v1/ponto/me/batidas", headers=h).json()
    assert hist["total"] >= 1
    it = hist["intervalos"][0]
    assert it["aberto"] is False
    assert "segundos_pausa" in it
    assert hist["total_segundos_pausa"] >= 0
    # Histórico inclui pausa_fim (sistema) implícito nos intervalos
    tipos = []
    # batidas raw via ajuste list — intervalos já fecharam
    assert it["saida_em"] is not None
    bats = client.get(
        "/v1/ponto/batidas",
        headers=auth_headers["admin"],
        params={"atendente_id": seed_base["a1"].id, "limit": 50},
    )
    assert bats.status_code == 200
    tipos = [b["tipo"] for b in bats.json()["items"]]
    assert "pausa_inicio" in tipos
    assert "pausa_fim" in tipos
    assert "saida" in tipos
    auto = next(b for b in bats.json()["items"] if b["tipo"] == "pausa_fim")
    assert auto.get("origem") == "sistema"


def test_ponto_ajuste_admin_e_403(client, seed_base, auth_headers):
    a1 = seed_base["a1"]
    r403 = client.post(
        "/v1/ponto/batidas",
        headers=auth_headers["a1"],
        json={
            "atendente_id": a1.id,
            "tipo": "entrada",
            "registrado_em": "2026-08-20T12:00:00+00:00",
            "motivo": "esquecimento",
        },
    )
    assert r403.status_code == 403

    r = client.post(
        "/v1/ponto/batidas",
        headers=auth_headers["admin"],
        json={
            "atendente_id": a1.id,
            "tipo": "entrada",
            "registrado_em": "2026-08-20T12:00:00+00:00",
            "motivo": "esquecimento de batida",
        },
    )
    assert r.status_code == 201, r.text
    bid = r.json()["id"]

    r2 = client.patch(
        f"/v1/ponto/batidas/{bid}",
        headers=auth_headers["admin"],
        json={"registrado_em": "2026-08-20T12:05:00+00:00", "motivo": "hora errada"},
    )
    assert r2.status_code == 200

    r3 = client.post(
        f"/v1/ponto/batidas/{bid}/anular",
        headers=auth_headers["admin"],
        json={"motivo": "batida duplicada"},
    )
    assert r3.status_code == 200
    assert r3.json()["anulada"] is True


def test_ponto_export_csv(client, seed_base, auth_headers):
    client.post("/v1/ponto/bater", headers=auth_headers["a1"], json={"tipo": "entrada"})
    client.post("/v1/ponto/bater", headers=auth_headers["a1"], json={"tipo": "saida"})
    r = client.get("/v1/ponto/batidas/export.csv", headers=auth_headers["admin"])
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    text = r.content.decode("utf-8-sig")
    assert "atendente" in text
    assert "trabalhado_min" in text
    r403 = client.get("/v1/ponto/batidas/export.csv", headers=auth_headers["a1"])
    assert r403.status_code == 403


def test_ponto_justificativa_fluxo(client, seed_base, auth_headers):
    a1 = seed_base["a1"]
    r = client.post(
        "/v1/ponto/justificativas",
        headers=auth_headers["a1"],
        json={"data_ref": "2026-08-19", "tipo": "esquecimento", "motivo": "Esqueci de bater saída"},
    )
    assert r.status_code == 201, r.text
    jid = r.json()["id"]

    r_me = client.get("/v1/ponto/justificativas/me", headers=auth_headers["a1"])
    assert r_me.status_code == 200
    assert any(j["id"] == jid for j in r_me.json())

    r403 = client.post(
        f"/v1/ponto/justificativas/{jid}/decidir",
        headers=auth_headers["a1"],
        json={"estado": "aprovada", "decisao_motivo": "ok"},
    )
    assert r403.status_code == 403

    r_ok = client.post(
        f"/v1/ponto/justificativas/{jid}/decidir",
        headers=auth_headers["admin"],
        json={
            "estado": "aprovada",
            "decisao_motivo": "Confirmado com o gestor",
            "aplicar_batidas": [
                {
                    "tipo": "saida",
                    "registrado_em": "2026-08-19T21:00:00+00:00",
                    "motivo": "saída esquecida",
                }
            ],
        },
    )
    assert r_ok.status_code == 200, r_ok.text
    assert r_ok.json()["estado"] == "aprovada"


def test_ponto_alertas_me(client, seed_base, auth_headers, db_session):
    a1 = seed_base["a1"]
    a1.usa_escala = True
    a1.escala_horas_trabalho = 12
    a1.escala_horas_folga = 36
    a1.escala_inicio_em = date(2026, 8, 1)
    from datetime import datetime, timezone

    a1.presenca_heartbeat_em = datetime.now(timezone.utc)
    a1.presenca_online_desde = a1.presenca_heartbeat_em
    db_session.add(a1)
    db_session.commit()

    r = client.get("/v1/ponto/me/alertas", headers=auth_headers["a1"])
    assert r.status_code == 200
    body = r.json()
    assert "mensagens" in body
    assert body["online_sem_ponto"] is True


def test_ponto_horario_atraso_e_feriado(client, seed_base, auth_headers):
    a1 = seed_base["a1"]
    r = client.patch(
        f"/v1/atendentes/{a1.id}",
        headers=auth_headers["admin"],
        json={
            "usa_escala": True,
            "escala_horas_trabalho": 12,
            "escala_horas_folga": 36,
            "escala_inicio_em": "2026-01-01",
            "horario_previsto_entrada": "08:00",
            "horario_previsto_saida": "20:00",
            "tolerancia_atraso_minutos": 10,
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["horario_previsto_entrada"] == "08:00"
    assert r.json()["tolerancia_atraso_minutos"] == 10

    r_ent = client.post(
        "/v1/ponto/batidas",
        headers=auth_headers["admin"],
        json={
            "atendente_id": a1.id,
            "tipo": "entrada",
            "registrado_em": "2026-01-03T12:00:00-03:00",
            "motivo": "entrada de teste atraso",
        },
    )
    assert r_ent.status_code == 201, r_ent.text
    r_sai = client.post(
        "/v1/ponto/batidas",
        headers=auth_headers["admin"],
        json={
            "atendente_id": a1.id,
            "tipo": "saida",
            "registrado_em": "2026-01-03T20:00:00-03:00",
            "motivo": "saída de teste",
        },
    )
    assert r_sai.status_code == 201, r_sai.text

    cal = client.get(
        "/v1/ponto/me/calendario",
        headers=auth_headers["a1"],
        params={"ano": 2026, "mes": 1},
    )
    assert cal.status_code == 200
    dia = next(d for d in cal.json()["dias"] if d["data"] == "2026-01-03")
    assert dia["atrasado"] is True
    assert dia["status"] == "atraso"
    assert dia["classe_visual"] in ("abaixo", "ok", "he")
    assert dia["segundos_trabalhados"] >= 0
    assert cal.json().get("jornada_diaria_minutos", 480) >= 60

    fer = client.post(
        "/v1/ponto/feriados",
        headers=auth_headers["admin"],
        json={"data": "2026-01-05", "nome": "Feriado teste"},
    )
    assert fer.status_code == 201, fer.text
    cal2 = client.get(
        "/v1/ponto/me/calendario",
        headers=auth_headers["a1"],
        params={"ano": 2026, "mes": 1},
    )
    dia_f = next(d for d in cal2.json()["dias"] if d["data"] == "2026-01-05")
    assert dia_f["feriado"] is True
    assert dia_f["status"] == "feriado"


def test_ponto_banco_digest_settings_fecho(client, seed_base, auth_headers, db_session):
    a1 = seed_base["a1"]
    client.patch(
        f"/v1/atendentes/{a1.id}",
        headers=auth_headers["admin"],
        json={
            "usa_escala": True,
            "escala_horas_trabalho": 8,
            "escala_horas_folga": 40,
            "escala_inicio_em": "2026-08-01",
            "horario_previsto_entrada": "09:00",
            "horario_previsto_saida": "17:00",
        },
    )
    client.post(
        "/v1/ponto/batidas",
        headers=auth_headers["admin"],
        json={
            "atendente_id": a1.id,
            "tipo": "entrada",
            "registrado_em": "2026-08-03T09:00:00-03:00",
            "motivo": "banco entrada",
        },
    )
    client.post(
        "/v1/ponto/batidas",
        headers=auth_headers["admin"],
        json={
            "atendente_id": a1.id,
            "tipo": "saida",
            "registrado_em": "2026-08-03T18:00:00-03:00",
            "motivo": "banco saída",
        },
    )

    bh = client.get(
        "/v1/ponto/me/banco-horas",
        headers=auth_headers["a1"],
        params={"desde": "2026-08-01", "ate": "2026-08-31"},
    )
    assert bh.status_code == 200, bh.text
    body = bh.json()
    assert body["segundos_realizados"] > 0
    assert "saldo_segundos" in body

    dig = client.get("/v1/ponto/digest", headers=auth_headers["admin"])
    assert dig.status_code == 200
    assert "faltas" in dig.json()
    assert "justificativas_pendentes" in dig.json()

    st = client.get("/v1/ponto/settings", headers=auth_headers["admin"])
    assert st.status_code == 200
    assert st.json()["fecho_automatico_ativo"] is False

    st2 = client.patch(
        "/v1/ponto/settings",
        headers=auth_headers["admin"],
        json={"fecho_automatico_ativo": True, "fecho_apos_horas": 4},
    )
    assert st2.status_code == 200
    assert st2.json()["fecho_automatico_ativo"] is True

    from datetime import datetime, timedelta, timezone

    from app.services.ponto_settings import processar_fecho_automatico

    client.post(
        "/v1/ponto/batidas",
        headers=auth_headers["admin"],
        json={
            "atendente_id": a1.id,
            "tipo": "entrada",
            "registrado_em": (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(),
            "motivo": "jornada antiga",
        },
    )
    n = processar_fecho_automatico(db_session, limit=10)
    assert n >= 1
    db_session.commit()
    me = client.get("/v1/ponto/me", headers=auth_headers["a1"])
    assert me.json()["em_jornada"] is False
