"""Lote F ponto: export folha RH (#975) e cobertura de plantão (#970)."""

from datetime import date, timedelta


def _patch_jornada_hoje(client, headers, atendente_id: int, *, ativo=True):
    keys = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]
    hoje_key = keys[date.today().weekday()]
    # Semanal exige pelo menos um dia ativo
    outro = keys[(date.today().weekday() + 1) % 7]
    hs = {k: {"ativo": False, "inicio": "08:00", "fim": "18:00"} for k in keys}
    hs[hoje_key] = {"ativo": ativo, "inicio": "08:00", "fim": "18:00"}
    if not ativo:
        hs[outro] = {"ativo": True, "inicio": "08:00", "fim": "18:00"}
    return client.patch(
        f"/v1/atendentes/{atendente_id}",
        headers=headers,
        json={
            "modo_jornada": "semanal",
            "usa_escala": True,
            "horario_semana": hs,
            "tolerancia_atraso_minutos": 15,
        },
    )


def test_export_folha_csv_colunas(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    desde = date.today().replace(day=1).isoformat()
    ate = date.today().isoformat()
    r = client.get(
        "/v1/ponto/export/folha.csv",
        headers=admin,
        params={"desde": desde, "ate": ate},
    )
    assert r.status_code == 200, r.text
    assert "text/csv" in r.headers.get("content-type", "")
    text = r.content.decode("utf-8-sig")
    header = text.splitlines()[0]
    for col in (
        "matricula",
        "nome",
        "previsto_horas",
        "realizado_horas",
        "atrasos",
        "faltas",
        "he_minutos",
        "banco_horas",
        "ajustes",
    ):
        assert col in header


def test_export_folha_xlsx(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    desde = date.today().replace(day=1).isoformat()
    ate = date.today().isoformat()
    r = client.get(
        "/v1/ponto/export/folha.xlsx",
        headers=admin,
        params={"desde": desde, "ate": ate},
    )
    assert r.status_code == 200, r.text
    assert r.content[:2] == b"PK"  # zip/xlsx


def test_cobertura_fluxo_solicitar_aceitar_homologar(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    a1h = auth_headers["a1"]
    a2h = auth_headers["a2"]
    a1 = seed_base["a1"]
    a2 = seed_base["a2"]
    assert _patch_jornada_hoje(client, admin, a1.id, ativo=True).status_code == 200
    assert _patch_jornada_hoje(client, admin, a2.id, ativo=False).status_code == 200

    data_ref = date.today().isoformat()
    sol = client.post(
        "/v1/ponto/coberturas",
        headers=a1h,
        json={"cobertor_id": a2.id, "data_ref": data_ref, "motivo": "Consulta médica"},
    )
    assert sol.status_code == 201, sol.text
    cob_id = sol.json()["id"]
    assert sol.json()["estado"] == "pendente_cobertor"

    resp = client.post(
        f"/v1/ponto/coberturas/{cob_id}/responder",
        headers=a2h,
        json={"aceitar": True},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["estado"] == "pendente_admin"

    dec = client.post(
        f"/v1/ponto/coberturas/{cob_id}/decidir",
        headers=admin,
        json={"aprovar": True},
    )
    assert dec.status_code == 200, dec.text
    assert dec.json()["estado"] == "aprovada"

    hoje = date.today()
    cal1 = client.get(
        "/v1/ponto/me/calendario",
        headers=a1h,
        params={"ano": hoje.year, "mes": hoje.month},
    )
    assert cal1.status_code == 200, cal1.text
    dia1 = next(d for d in cal1.json()["dias"] if d["data"] == data_ref)
    assert dia1["esperado"] is False
    assert dia1["status"] != "falta"

    cal2 = client.get(
        "/v1/ponto/me/calendario",
        headers=a2h,
        params={"ano": hoje.year, "mes": hoje.month},
    )
    assert cal2.status_code == 200, cal2.text
    dia2 = next(d for d in cal2.json()["dias"] if d["data"] == data_ref)
    assert dia2["esperado"] is True


def test_cobertura_admin_conceder(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    a1 = seed_base["a1"]
    a2 = seed_base["a2"]
    data_ref = (date.today() + timedelta(days=1)).isoformat()
    r = client.post(
        "/v1/ponto/coberturas/conceder",
        headers=admin,
        json={
            "solicitante_id": a1.id,
            "cobertor_id": a2.id,
            "data_ref": data_ref,
            "motivo": "Plantão urgente",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["estado"] == "aprovada"
    assert r.json()["origem"] == "admin"


def test_cobertura_colegas_e_me(client, seed_base, auth_headers):
    a1h = auth_headers["a1"]
    cols = client.get("/v1/ponto/coberturas/colegas", headers=a1h)
    assert cols.status_code == 200, cols.text
    ids = {c["id"] for c in cols.json()}
    assert seed_base["a1"].id not in ids
    assert seed_base["a2"].id in ids

    me = client.get("/v1/ponto/coberturas/me", headers=a1h)
    assert me.status_code == 200
