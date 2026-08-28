"""Lote E: ausências (#976), pausa mínima (#973), anexo justificativa (#977)."""

from datetime import date, datetime, timedelta, timezone
from io import BytesIO

from app.services.escala import PONTO_TZ


def _patch_jornada_semanal(client, headers, atendente_id: int, *, fim="18:00"):
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


def test_ausencia_admin_agenda_sem_falta(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    a1 = seed_base["a1"]
    assert _patch_jornada_semanal(client, admin, a1.id).status_code == 200
    hoje = date.today()
    r = client.post(
        "/v1/ponto/ausencias/conceder",
        headers=admin,
        json={
            "atendente_id": a1.id,
            "tipo": "ferias",
            "desde": hoje.isoformat(),
            "ate": hoje.isoformat(),
            "motivo": "Recesso",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["estado"] == "aprovada"
    cal = client.get(
        f"/v1/ponto/me/calendario?ano={hoje.year}&mes={hoje.month}",
        headers=user,
    )
    assert cal.status_code == 200
    dia = next(d for d in cal.json()["dias"] if d["data"] == hoje.isoformat())
    assert dia["status"] == "ferias"
    assert dia["esperado"] is False
    assert dia["classe_visual"] == "ausencia"


def test_colaborador_solicita_folga_admin_aprova(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    amanha = date.today() + timedelta(days=1)
    sol = client.post(
        "/v1/ponto/ausencias",
        headers=user,
        json={
            "tipo": "folga_programada",
            "desde": amanha.isoformat(),
            "ate": amanha.isoformat(),
            "motivo": "Compromisso",
        },
    )
    assert sol.status_code == 201, sol.text
    assert sol.json()["estado"] == "pendente"
    pend = client.get("/v1/ponto/ausencias?estado=pendente", headers=admin)
    assert any(x["id"] == sol.json()["id"] for x in pend.json())
    dec = client.post(
        f"/v1/ponto/ausencias/{sol.json()['id']}/decidir",
        headers=admin,
        json={"aprovar": True},
    )
    assert dec.status_code == 200
    assert dec.json()["estado"] == "aprovada"


def test_pausa_minima_flag_calendario(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    a1 = seed_base["a1"]
    assert client.patch(
        "/v1/ponto/settings",
        headers=admin,
        json={"pausa_minima_minutos": 60},
    ).status_code == 200
    agora = datetime(2026, 6, 17, 14, 0, tzinfo=PONTO_TZ)
    t0 = agora.replace(hour=8, minute=0, second=0, microsecond=0)
    seq = [
        ("entrada", t0),
        ("pausa_inicio", t0 + timedelta(hours=2)),
        ("pausa_fim", t0 + timedelta(hours=2, minutes=10)),
        ("saida", t0 + timedelta(hours=4)),
    ]
    for tipo, when in seq:
        r = client.post(
            "/v1/ponto/batidas",
            headers=admin,
            json={
                "atendente_id": a1.id,
                "tipo": tipo,
                "registrado_em": when.astimezone(timezone.utc).isoformat(),
                "motivo": "teste pausa mínima",
            },
        )
        assert r.status_code == 201, f"{tipo}: {r.text}"
    hoje = agora.date()
    cal = client.get(
        f"/v1/ponto/me/calendario?ano={hoje.year}&mes={hoje.month}",
        headers=user,
    )
    assert cal.status_code == 200
    dia = next(d for d in cal.json()["dias"] if d["data"] == hoje.isoformat())
    assert dia["pausa_abaixo_minimo"] is True
    assert dia["segundos_pausa"] < 60 * 60


def test_justificativa_com_anexo_pdf(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    pdf = b"%PDF-1.4 fake test content"
    r = client.post(
        "/v1/ponto/justificativas/upload",
        headers=user,
        data={
            "data_ref": date.today().isoformat(),
            "tipo": "falta",
            "motivo": "Atestado médico",
        },
        files={"arquivo": ("atestado.pdf", BytesIO(pdf), "application/pdf")},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["tem_anexo"] is True
    assert body["anexo_nome"]
    dl = client.get(f"/v1/ponto/justificativas/{body['id']}/anexo", headers=admin)
    assert dl.status_code == 200
    assert dl.content == pdf
