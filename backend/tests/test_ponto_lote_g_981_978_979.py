"""Lote G ponto: setup (#981), competência (#978), ciência (#979)."""

from datetime import date, datetime, timezone


def test_setup_status_admin(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    r = client.get("/v1/ponto/setup-status", headers=admin)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "itens" in body
    assert body["defaults_fecho_off"] is True
    assert body["tolerancia_sugerida_minutos"] == 15
    assert any(i["codigo"] == "jornada_colaboradores" for i in body["itens"])


def test_competencia_fechar_reabrir_e_ajuste_pos(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    a1 = seed_base["a1"]
    hoje = date.today()
    ano, mes = hoje.year, hoje.month

    fech = client.post(f"/v1/ponto/competencias/{ano}/{mes}/fechar", headers=admin)
    assert fech.status_code == 200, fech.text
    assert fech.json()["fechada"] is True

    getc = client.get(f"/v1/ponto/competencias/{ano}/{mes}", headers=admin)
    assert getc.json()["fechada"] is True

    ajuste = client.post(
        "/v1/ponto/batidas",
        headers=admin,
        json={
            "atendente_id": a1.id,
            "tipo": "entrada",
            "registrado_em": datetime.now(timezone.utc).isoformat(),
            "motivo": "Correção pós-fechamento",
        },
    )
    assert ajuste.status_code == 201, ajuste.text

    reab = client.post(
        f"/v1/ponto/competencias/{ano}/{mes}/reabrir",
        headers=admin,
        json={"motivo": "Erro no fechamento"},
    )
    assert reab.status_code == 200, reab.text
    assert reab.json()["fechada"] is False


def test_ciencia_somente_apos_fechamento(client, seed_base, auth_headers):
    admin = auth_headers["admin"]
    user = auth_headers["a1"]
    hoje = date.today()
    # Usa mês passado para não conflitar com teste anterior no mesmo worker
    if hoje.month == 1:
        ano, mes = hoje.year - 1, 12
    else:
        ano, mes = hoje.year, hoje.month - 1

    bloqueado = client.post(f"/v1/ponto/me/ciencia?ano={ano}&mes={mes}", headers=user)
    assert bloqueado.status_code == 400

    assert client.post(f"/v1/ponto/competencias/{ano}/{mes}/fechar", headers=admin).status_code == 200

    ok = client.post(f"/v1/ponto/me/ciencia?ano={ano}&mes={mes}", headers=user)
    assert ok.status_code == 200, ok.text
    assert ok.json()["confirmada"] is True

    lista = client.get(f"/v1/ponto/competencias/{ano}/{mes}/ciencias", headers=admin)
    assert lista.status_code == 200
    a1 = seed_base["a1"]
    item = next(i for i in lista.json() if i["atendente_id"] == a1.id)
    assert item["confirmada"] is True

    me = client.get(f"/v1/ponto/me/ciencia?ano={ano}&mes={mes}", headers=user)
    assert me.json()["confirmada"] is True
    assert me.json()["pode_confirmar"] is False
